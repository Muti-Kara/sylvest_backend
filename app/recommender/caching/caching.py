from django_redis import get_redis_connection
from redis import Redis

from api.helper import Singleton


class CacheManager(metaclass=Singleton):
    cache: Redis

    def __init__(self) -> None:
        self.cache: Redis = get_redis_connection()

    def add_relation(self, relation: str, subject_id: int, item_id: int, unique: bool = False) -> bool:
        if unique:
            return self.cache.set(f"{relation}:{subject_id}", item_id) == 1
        return self.cache.sadd(f"{relation}:{subject_id}", item_id) == 1

    def rem_relation(self, relation: str, subject_id: int, item_id: int, unique: bool = False) -> bool:
        if unique:
            return self.cache.delete(f"{relation}:{subject_id}") == 1
        return self.cache.srem(f"{relation}:{subject_id}", item_id) == 1

    def get_relation(self, relation: str, subject_id: int, unique: bool = False) -> set:
        if unique:
            return self.cache.get(f"{relation}:{subject_id}")
        return self.cache.smembers(f"{relation}:{subject_id}")

    def delete_regex(self, reg_expression: str) -> int:
        count: int = 0
        for key in self.cache.scan_iter(reg_expression):
            self.cache.delete(key)
            count += 1
        return count

    @staticmethod
    def u2u_to_dict(db: Redis) -> dict:
        raise NotImplementedError()

    @staticmethod
    def u2p_to_dict(db: Redis) -> dict:
        u2p_dict: dict = dict()
        u2p_dict["users"] = set()
        u2p_dict["posts"] = set()
        u2p_dict["relations"] = dict()
        for key in db.scan_iter("u2p*"):
            user_id = int(str(key).split(':')[1][:-1])
            post_set: set = set(map(int, db.smembers(key)))
            u2p_dict["users"].add(user_id)
            u2p_dict["posts"].update(post_set)
            u2p_dict["relations"].update({user_id: post_set})
        return u2p_dict

    @staticmethod
    def u2c_to_dict(db: Redis) -> dict:
        raise NotImplementedError()
