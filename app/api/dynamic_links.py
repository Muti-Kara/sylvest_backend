import json
from requests import post, Response

class DynamicLinkManager:
    def __init__(self) -> None:
        self.api_key: str = "AIzaSyBKZql6kCW_T_Tv5RwC_QoY5RGpXYkAVTw"
        self.domain_name: str = "https://thesylvest.com"
        self.link_domain: str = "https://sylvetapp.page.link"
    
    def __build_request_params(self, item_id: int, link_type: str) -> dict:
        return {
            "dynamicLinkInfo": {
                "domainUriPrefix": self.link_domain,
                "link": f"{self.domain_name}/{link_type}/{item_id}",
                "androidInfo": {
                    "androidPackageName": "com.example.sylvet_app"
                },
                "iosInfo": {
                    "iosBundleId": "com.example.sylvetApp"
                }
            }
        }
        
    def __firebase_link(self) -> str:
        return r"https://firebasedynamiclinks.googleapis.com/v1/shortLinks?key=" + self.api_key
    
    def create_link(self, *, item_id: int, link_type: str = "post") -> str:
        params: dict = self.__build_request_params(item_id, link_type)
        firebase_link = self.__firebase_link()
        
        response: Response = post(url=firebase_link, json=params)
        
        content: dict = json.loads(response.content)
        print(content)
        
        return content["shortLink"]