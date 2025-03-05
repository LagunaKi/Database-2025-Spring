from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import schemas
import requests


app = FastAPI()


URL = 'http://[HOST]:[PORT]/v1'
MODEL = '[MODEL]'


@app.post("/chat/stream/")
async def chat_stream(conversation: schemas.Conversation):

    def generator():
        with requests.post(f'{URL}/chat/completions', json={
            'model': MODEL,
            'stream': True,
            'messages': [m.model_dump() for m in conversation.messages],
        }, stream=True, timeout=60) as resp:
            for raw_line in resp.iter_lines():
                line = raw_line.decode('utf-8').strip()
                if line == '':
                    continue
                if line.startswith('data: '):
                    line = line[len('data: '):]
                    if line == '[DONE]':
                        yield raw_line + b'\n'
                        break
                else:
                    yield raw_line + b'\n'
                    break
                # print(json.loads(line))
                yield raw_line + b'\n'
    
    return StreamingResponse(generator())


@app.post("/chat/", response_model=schemas.ConversationResponse)
async def chat(conversation: schemas.Conversation):
    resp = requests.post(f'{URL}/chat/completions', json={
        'model': MODEL,
        'stream': False,
        'messages': [m.model_dump() for m in conversation.messages],
    }, stream=False, timeout=60)
    return resp.json()
