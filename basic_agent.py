import concurrent.futures
import inspect
import json
import logging
import os.path
import re
import sys
import time

import yaml
from regex import regex

import llm_base


def _format_text(raw, inputs: dict):
    regex = re.compile('(\?([^\{]+)\{([^\}]+)\}\?)')
    matches = regex.findall(raw)
    for match in matches:
        contains = False
        for key, value in inputs.items():
            if key in match[1] and value:
                raw = raw.replace(match[0], match[2])
                contains = True
                break
        if not contains:
            raw = raw.replace(match[0], '')

    for key, value in inputs.items():
        if value is not None and (isinstance(value, str) or isinstance(value, int)):
            raw = raw.replace(f'{{{key}}}', str(value))
    regex = re.compile(r'\{[^\}]+\}')
    matches = regex.findall(raw)
    for match in matches:
        raw = raw.replace(match, '')
    raw = re.sub(r'\n+', '\n', raw)
    return raw.strip()


def _extract_list(resp):
    regex = re.compile(r'\d[^:：\.\s]*[:：\.](.*?)[\r\n]')
    options = regex.findall(resp + '\n')
    options = list((x for x in options))
    return options


def _extract_option(resp):
    regex = re.compile(r'\d[^:：\.\s]*[:：\.](.*?)[\r\n]')
    options = regex.findall(resp + '\n')
    options = list((f"{i + 1}. {x}" for i, x in enumerate(options)))
    return options


def _extract_attr(resp, name):
    regex = re.compile(rf'{name}[^:：\.\s]*[:：\.](.*?)[\r\n]')
    attr = regex.findall(resp + '\n')
    if len(attr) == 0:
        return None
    else:
        return attr[0]


def _remove_options(resp):
    regex = re.compile(r'\d[^:：\.\s]*[:：\.](.*?)[\r\n]')
    options = regex.findall(resp + '\n')
    resp_lines = resp.split('\n')
    new_resp = ""
    for line in resp_lines:
        stop = False
        for option in options:
            if option in line:
                stop = True
                break
        if stop:
            break
        new_resp += line + '\n'
    return new_resp.strip()


class BasicAgent:
    config_path = "nope"
    name = "nope"
    model_preset = "deepseek"
    prompt_args = {}

    def __init__(self):
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        self._history = []
        self._stream_callback = None
        origin_path = os.path.dirname(inspect.getfile(self.__class__))
        with open(os.path.join(origin_path, self.config_path), 'r') as f:
            self.config = yaml.safe_load(f)[self.name]

    def set_context(self, context):
        self._history = context
        return self

    def set_stream_callback(self, stream_callback):
        self._stream_callback = stream_callback
        return self

    def add_assistant_history(self, message):
        self._history.append({'role': 'assistant', 'content': message})
        return self

    def add_user_history(self, message):
        self._history.append({'role': 'user', 'content': message})
        return self

    def format_text(self, name, inputs={}):
        self.logger.info(f"format_args: {name}, {inputs}")
        text = _format_text(self.config[name], inputs)
        self.logger.info(f"format_text: {text}")
        return text

    def system_prompt(self, **kwargs):
        return self.format_text('system_prompt', {**self.prompt_args, **kwargs})

    def task_prompt(self, **kwargs):
        return self.format_text('task_prompt', {**self.prompt_args, **kwargs})

    def kickoff(self, **kwargs):
        resp, _ = llm_base.llm(self.system_prompt(**kwargs), self.task_prompt(**kwargs), history=self._history,
                               preset=self.model_preset, content_callback=self._stream_callback)
        self.logger.info(f"Kickoff: {resp}")
        return resp

    def kickoff_list(self, **kwargs):
        retry_times = 0
        results = None
        while retry_times < 3:
            try:
                resp = self.kickoff(**kwargs)
                results = _extract_list(resp)
                if not results:
                    raise ValueError("List empty!")
                break
            except Exception as e:
                self.logger.error(f"Retry:{retry_times},Error in kickoff: {e}")
                retry_times += 1
                time.sleep(1)
        if not results:
            raise ValueError("Failed to get lists from kickoff")
        return results


def _extract_progress(resp):
    progress_regex = regex.compile(r'进度[^\r\n\d]*(\d+)%')
    progress = progress_regex.search(resp)
    if progress:
        stage = int(progress.group(1))
        return stage
    return None


class PlayAgent:
    config_path = "nope"
    name = "nope"
    model_preset = "deepseek"
    default_options = []
    stop_words = None

    def __init__(self, **kwargs):
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        self.prompt_args = dict(kwargs)
        self._history = []
        origin_path = os.path.dirname(inspect.getfile(self.__class__))
        with open(os.path.join(origin_path, self.config_path), 'r') as f:
            self.config = yaml.safe_load(f)[self.name]
        self._options_context = {}
        self._options_branch = ["main"]
        self._last_options = []
        self._sub_agent = None
        self._parent_agent = None
        self._quit_msg = None

    def set_parent(self, parent_agent):
        self._parent_agent = parent_agent
        return self

    def set_sub(self, sub_agent):
        self._sub_agent = sub_agent
        if sub_agent:
            sub_agent.set_parent(self)
        return self

    def set_context(self, context):
        self._history = context
        return self

    def add_history(self, role, content):
        self._history.append({'role': role, 'content': content})
        return self

    def _format_text(self, name, inputs={}):
        self.logger.info(f"format_args: {name}, {inputs}")
        result = _format_text(self.config[name], inputs)
        self.logger.info(f"format_text: {result}")
        return result

    def _system_prompt(self, **kwargs):
        return self._format_text('system_prompt', {**self.prompt_args, **kwargs})

    def _startup_prompt(self, **kwargs):
        return self._format_text('startup_prompt', {**self.prompt_args, **kwargs})

    def _summary_prompt(self, **kwargs):
        if 'summary_prompt' in self.config:
            return self._format_text('summary_prompt', {**self.prompt_args, **kwargs})
        return None

    def _play_prompt(self, **kwargs):
        return self._format_text('play_prompt', {**self.prompt_args, **kwargs})

    def open_branch(self, name, only=False):
        if only:
            self._options_branch = [name]
        else:
            self._options_branch.append(name)

    def close_branch(self, name):
        self._options_branch.remove(name)

    def startup(self, stream_callback=None, **kwargs):
        next_options = self._next_options()
        resp, _ = llm_base.llm(self._system_prompt(), self._startup_prompt(**kwargs),
                               history=self._history,
                               preset=self.model_preset,
                               content_callback=stream_callback,
                               stop_words=self.stop_words)
        self._last_options = next_options
        return resp, next_options

    def quit(self, **kwargs):
        if self._parent_agent:
            self._quit_msg = self._format_text('summary', {**self.prompt_args, **kwargs})

    def on_sub_quit(self, **kwargs):
        pass

    def play(self, option, extra_input, stream_callback=None,**kwargs):
        extra_args = {}
        if self._sub_agent:
            resp, options = self._sub_agent.play(option, extra_input, stream_callback)
            if not self._sub_agent._quit_msg:
                return resp, options
            else:
                extra_args['sub_summary'] = self._sub_agent._quit_msg
                player_action = None
                self._sub_agent = None
                self.on_sub_quit(**extra_args)
        else:
            action_value = option
            player_action = extra_input
            branch = action_value.split('_')[0]
            if hasattr(self, 'play_' + branch):
                extra_args = getattr(self, 'play_' + branch)(action_value, player_action)
            if self._quit_msg is not None:
                return "", []
            if not extra_args:
                extra_args = {}
            if self._sub_agent:
                return self._sub_agent.startup(stream_callback)
        next_options = self._next_options()

        def req(content_callback):
            _resp, _ = llm_base.llm(self._system_prompt(),
                                    self._play_prompt(player_action=player_action,
                                                      player_option=self._format_text(option), **extra_args,**kwargs),
                                    history=self._history,
                                    preset=self.model_preset, content_callback=content_callback,
                                    stop_words=self.stop_words)
            return _resp

        with concurrent.futures.ThreadPoolExecutor() as executor:
            fut_summary = self._compress_history(executor)
            if fut_summary:
                fut_req = executor.submit(req, stream_callback)
                concurrent.futures.wait([fut_summary, fut_req], return_when=concurrent.futures.ALL_COMPLETED)
                resp = fut_req.result()
                history_summary = fut_summary.result()
                if history_summary:
                    self._history = history_summary + self._history[-2:]
            else:
                resp = req(stream_callback)

        self._last_options = next_options
        return resp, next_options

    def _next_options(self):
        next_options = []
        self._options_context = {}
        for branch in self._options_branch:
            for key, value in self.config.items():
                if key.startswith(f"{branch}_option"):
                    next_options.append({'value': key})
        for i, option in enumerate(next_options):
            option['label'] = f"{self._format_text(option['value'], self.prompt_args)}".strip()
            self._options_context[option['value']] = option
        return next_options

    def _compress_history(self, executor):
        keep = [self._history[0]]
        history = []
        for msg in self._history[1:]:
            if msg['role'] == 'assistant':
                if '历史记录已压缩' in msg['content']:
                    keep.append(msg)
                    continue
                history.append({'role': 'assistant', 'content': _remove_options(msg['content'])})
            elif msg['role'] == 'user':
                history.append({'role': 'user', 'content': msg['content'].strip().split('\n')[0]})
        if len(history) < 6:
            return None
        summary_prompt = self._summary_prompt()
        if summary_prompt is None:
            return None

        def summary():
            resp, _ = llm_base.llm("你要压缩对话记录",
                                   summary_prompt,
                                   history=history,
                                   preset=self.model_preset)
            self.logger.info(f"Summary: {resp}")
            _history = keep + [{'role': 'assistant', 'content': "历史记录已压缩，以下是压缩后的历史记录：\n" + resp}]
            return _history

        return executor.submit(summary)

    def debug(self):
        return json.dumps(self._history, ensure_ascii=False, indent=2)

    def last_options(self):
        return self._last_options