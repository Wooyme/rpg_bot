import datetime
import json
import logging
import sys
import time
import traceback

import httpx
from httpx import Timeout

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler(stream=sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# nsfw support models = ["alpindale/magnum-72b","nousresearch/hermes-3-llama-3.1-405b:extended","microsoft/wizardlm-2-8x22b"]


with open('config.json') as f:
    llm_presets = json.load(f)['llm_presets']


def llm(system_prompt, user_prompt, preset='deepseek-deepinfra', history=None,
        stop_words=None, prefix_words=None, suffix_words=None, content_callback=None, hidden_words=None) -> (str, int):
    retry_times = 0
    while retry_times < 3:
        try:
            return _llm(system_prompt, user_prompt, preset, history, stop_words, prefix_words, suffix_words,
                        content_callback, hidden_words)
        except Exception as e:
            print(e)
            traceback.print_exc()
            retry_times += 1
            time.sleep(5)
    return "", 0


def _llm(system_prompt, user_prompt, preset, history=None,
         stop_words=None, prefix_words=None, suffix_words=None, content_callback=None, hidden_words=None) -> (str, int):
    httpx_client = httpx.Client(timeout=Timeout(timeout=15.0))
    if history is None:
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    else:
        history.append({"role": "user", "content": user_prompt})
        messages = [{"role": "system", "content": system_prompt}] + history
    if prefix_words is not None:
        messages.append({"role": "assistant", "content": prefix_words})
    from openai import OpenAI
    llm_preset = llm_presets[preset]
    client = OpenAI(
        base_url=llm_preset['base_url'],
        api_key=llm_preset['api_key'],
        http_client=httpx_client
    )
    response = client.chat.completions.create(
        model=llm_preset['model'],
        messages=messages,
        stream=True,
        temperature=llm_preset['temperature'],
        frequency_penalty=llm_preset['frequency_penalty'],
        presence_penalty=llm_preset['presence_penalty'],
        stop=stop_words,
    )
    collected_chunks = []
    collected_messages = []
    # iterate through the stream of events
    last_callback_time = datetime.datetime.now()

    for chunk in response:
        collected_chunks.append(chunk)  # save the event response
        chunk_message = chunk.choices[0].delta.content  # extract the message
        collected_messages.append(chunk_message)  # save the message
        if content_callback is not None and datetime.datetime.now() - last_callback_time > datetime.timedelta(
                seconds=3):
            content = ''.join(collected_messages)
            if hidden_words is not None:
                for word in hidden_words:
                    content = content.replace(word, '')
            if content:
                content_callback(content)
            last_callback_time = datetime.datetime.now()

    if content_callback is not None:
        time.sleep(1)
    content = ''.join(collected_messages)
    if hidden_words is not None:
        for word in hidden_words:
            content = content.replace(word, '')
    if history is not None:
        history.append({"role": "assistant", "content": content})
    if prefix_words is not None and not content.strip().startswith(prefix_words):
        content = prefix_words + content
    if suffix_words is not None and not content.strip().endswith(suffix_words):
        content = content + suffix_words
    content = content.replace('"[{', '[{').replace('}]": "', '}]')
    logger.debug("Response: %s", content)
    logger.debug("Usage: %s", collected_chunks[-1].usage.total_tokens)
    return content, collected_chunks[-1].usage.total_tokens


def advance_llm(history, model='qwen/qwen-2-7b-instruct', stop_words=None, prefix_words=None, suffix_words=None):
    def _llm(system_prompt: str, user_prompt: str):
        return llm(system_prompt, user_prompt, model, history, stop_words, prefix_words, suffix_words)

    return _llm
