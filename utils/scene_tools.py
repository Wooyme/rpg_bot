import hanlp
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

HanLP = hanlp.pipeline() \
    .append(hanlp.utils.rules.split_sentence, output_key='sentences') \
    .append(hanlp.load('FINE_ELECTRA_SMALL_ZH'), output_key='tok') \
    .append(hanlp.load('CTB9_POS_ELECTRA_SMALL'), output_key='pos') \
    .append(hanlp.load('MSRA_NER_ELECTRA_SMALL_ZH'), output_key='ner', input_key='tok') \
    .append(hanlp.load('CTB9_DEP_ELECTRA_SMALL', conll=0), output_key='dep', input_key='tok') \
    .append(hanlp.load('CTB9_CON_ELECTRA_SMALL'), output_key='con', input_key='tok')


def node_dfs(node, blocks, in_np='-'):
    if isinstance(node, str):
        blocks.append({"pos": in_np, 'text': node})
        return
    for sub in node:
        node_dfs(sub, blocks, in_np='n' if node._label == 'NP' or in_np == 'n' else '-')


def highlight_text(text):
    if not text:
        return JSONResponse({"error": "No text provided"}, status_code=400)
    nlp_result = HanLP(text)
    items = []
    for con in nlp_result['con']:
        node_dfs(con, items)
    enhanced_items = []
    current_item = {'pos': '-', 'text': ''}
    for item in items:
        if (('n' in item['pos'] and 'n' not in current_item['pos']) or
                ('n' not in item['pos'] and 'n' in current_item['pos'])):
            if current_item['text'] != '':
                enhanced_items.append(current_item.copy())
                current_item['text'] = ''
        current_item['pos'] = 'n' if 'n' in item['pos'] else '-'
        current_item['text'] += item['text']
    enhanced_items.append(current_item)
    return {"text": text, "items": enhanced_items, "sentences": nlp_result['sentences']}


async def highlight_scene(request):
    data = await request.json()
    text = data.get("text", "")

    return JSONResponse(highlight_text(text))


async def highlight_map(request):
    data = await request.json()
    location_list = data.get("location_list", [])
    if not location_list:
        return JSONResponse({"error": "No location_list provided"}, status_code=400)
    items = []
    for location in location_list:
        items.append({'pos': 'n', 'text': location['location_name']})
        items.append({'pos': '-',
                      'text': f":\n{location['location_description']}\n{location['location_type']}\n{location['location_path']}\n"})
    return JSONResponse({"text": "", "items": items, "sentences": ""})


routes = [
    Route('/highlight_scene', highlight_scene, methods=['POST']),
    Route('/highlight_map', highlight_map, methods=['POST']),
]

app = Starlette(routes=routes)
