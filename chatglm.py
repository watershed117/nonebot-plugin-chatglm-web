import httpx
import json

class Chatglm():
    def __init__(self,
                 token: str,
                 refresh_token:str,
                 acw_tc:str,
                 assistant_id:str,
                 timeout: int = 60,
                 conversation_id:str="") -> None:

        self.token=token
        self.acw_tc=acw_tc
        self.refresh_token=refresh_token
        self.timeout=timeout

        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Cookie': f'acw_tc={acw_tc}',
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
        }
        self.client = httpx.AsyncClient(timeout=timeout, headers=self.headers)
        self.assistant_id=assistant_id
        self.conversation_id=conversation_id
    async def send(self,message:str,conversation_id:str=""):
        payload = {
            "assistant_id": self.assistant_id,
            "conversation_id": conversation_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": message
                        }
                    ]
                }
            ],
            "meta_data": {
                "is_test": False,
                "input_question_type": "xxxx",
                "channel": "",
                "draft_id": ""
            }
        }
        async with self.client.stream(method="POST", url="https://chatglm.cn/chatglm/backend-api/assistant/stream", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                # print(line)
                if line.startswith("data:"):
                    data = json.loads(line[6:])
                    # print(data)
                    conversation_id = data.get("conversation_id")
                    parts = data.get("parts")
                    if parts:
                        # model=parts[0].get("model")
                        # logic_id=parts[0].get("logic_id")
                        content = parts[0].get("content")
                        if content:
                            text = content[0].get("text")
            # "logic_id":logic_id,"model":model}
            self.conversation_id=conversation_id
            return {"conversation_id": conversation_id, "text": text}

    async def delete(self,conversation_id:str):
        url = "https://chatglm.cn/chatglm/backend-api/assistant/conversation/delete"
        playload = {"assistant_id": {self.assistant_id},
                    "conversation_id": conversation_id}
        response=await self.client.post(url=url,json=playload)
        response.raise_for_status()
    async def recommand(self,conversation_id:str):
        url = f"https://chatglm.cn/chatglm/backend-api/v1/conversation/recommendation/list?conversation_id={conversation_id}"
        response=await self.client.get(url=url) 
        response.raise_for_status()
        return response.json().get("result").get("list")
    async def get_conversations(self,page:int=1,page_size:int=25):
        url=f"https://chatglm.cn/chatglm/backend-api/assistant/conversation/list?assistant_id={self.assistant_id}&page={page}&page_size={page_size}"
        response=await self.client.get(url=url)
        response.raise_for_status()
        conversation_list=response.json().get("result").get("conversation_list")
        if conversation_list:
            tmp_list=[]
            for conversation in conversation_list:
                assistant_id=conversation.get("assistant_id")
                conversation_id=conversation.get("id")
                title=conversation.get("title")
                tmp_list.append({"assistant_id":assistant_id,"conversation_id":conversation_id,"title":title})
            return [tmp_list,response.json().get("result").get("has_more") or False]
    async def get_history(self,conversation_id:str):
        url=f"https://chatglm.cn/chatglm/backend-api/assistant/conversation?assistant_id={self.assistant_id}&conversation_id={conversation_id}"
        response=await self.client.get(url=url)
        response.raise_for_status()
        messages=response.json().get("result").get("messages")
        tmp_list=[]
        for message in messages:
            input=message.get("input")
            text=input.get("content")[0].get("text")
            role=input.get("role")
            tmp_list.append({role:text})
            output=message.get("output")
            text=output.get("parts")[0].get("content")[0].get("text")
            role=output.get("role")
            tmp_list.append({role:text})
        return tmp_list
    async def refresh(self,refresh_token:str):
        url="https://chatglm.cn/chatglm/backend-api/v1/user/refresh"
        self.client.headers.update({'Authorization': f'Bearer {refresh_token}'})
        response=await self.client.post(url=url)
        response.raise_for_status
        # print(response.json())
        self.token=response.json().get("result").get("accessToken")
        self.acw_tc=response.cookies.get("acw_tc")
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Cookie': f'acw_tc={self.acw_tc}',
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
        }
        self.client = httpx.AsyncClient(timeout=self.timeout, headers=self.headers)
        return True

