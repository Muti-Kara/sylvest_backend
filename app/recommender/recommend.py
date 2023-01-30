from django.contrib.auth.models import User
from django.db.models import QuerySet

from api.helper import Singleton
from blog.models import MasterPost
from recommender.caching.caching import CacheManager
from recommender.ml_models.content_based import PostRecommender, UserRecommender
from subjects.models import Profile


class Recommender(metaclass=Singleton):
    following_bonus: float = 0.3

    def __init__(self) -> None:
        self.cache_manager = CacheManager()
        self.post_recommender = PostRecommender()
        self.user_recommender = UserRecommender()

    def update_posts(self) -> bool:
        try:
            self.post_recommender.calculate_similarity_matrix()
            self.cache_manager.delete_regex("temp*")
            return True
        except Exception as e:
            import traceback

            print(e, traceback.format_exc())
            return False

    def update_users(self) -> bool:
        try:
            self.user_recommender.calculate_similarity_matrix()
            self.cache_manager.delete_regex("temp*")
            return True
        except Exception as e:
            import traceback

            print(e, traceback.format_exc())
            return False

    def update_recommender(self) -> bool:
        return self.update_posts() and self.update_users()

    def add_post_relation(self, post: MasterPost) -> bool:
        return self.cache_manager.add_relation("posted", post.id, post.author.id, unique=True)

    def remove_post_relation(self, post: MasterPost) -> bool:
        return self.cache_manager.rem_relation("posted", post.id, post.author.id, unique=True)

    def __recommended_posts(self, user: User, depth: int = 0) -> dict:
        if not self.cache_manager.cache.exists("cached_posts:"):
            if depth > 4:
                raise Exception("Maximum depth reached")
            self.update_recommender()
            depth += 1
            return self.__recommended_posts(user, depth=depth)

        if user.is_anonymous or not self.cache_manager.cache.sismember("cached_users:", f"{user.id}"):
            raise Exception("User must be cached and not anonymous")

        if not self.cache_manager.cache.exists(f"temp:{user.id}"):
            self.cache_manager.cache.sinterstore(
                f"temp:{user.id}", f"u2p:{user.id}", "cached_posts:")

        rand_post = 1
        if self.cache_manager.cache.exists(f"temp:{user.id}"):
            rand_post = self.cache_manager.cache.srandmember(f"temp:{user.id}")
        else:
            rand_post = self.cache_manager.cache.srandmember("cached_posts:")

        if not rand_post:
            rand_post = 1

        post_scores: dict = self.post_recommender.recommend(int(rand_post))
        followings: set = self.cache_manager.get_relation("u2u", user.id)
        for p_id in post_scores.keys():
            if self.cache_manager.get_relation("posted", p_id, unique=True) in followings:
                post_scores[p_id] += self.following_bonus
        return post_scores

    def __recommended_users(self, user: User, __depth: int = 0) -> list[int]:
        if user.is_anonymous or not self.cache_manager.cache.sismember("cached_users:", f"{user.id}"):
            raise Exception("User must be cached and not anonymous")

        user_scores = self.user_recommender.recommend(user.id)
        return sorted(user_scores.keys(), key=lambda x: user_scores[x])

    def get_recommended_posts(self, user: User, posts: QuerySet[MasterPost]) -> QuerySet[MasterPost]:
        try:
            recommended_ids: dict = self.__recommended_posts(user)
            return posts.filter(id__in=recommended_ids)
        except Exception as e:
            import traceback

            print(e, traceback.format_exc())
            return posts

    def get_recommended_users(self, user: User) -> QuerySet[User] | None:
        try:
            recommended_ids: list[int] = self.__recommended_users(user)
            return Profile.objects.filter(id__in=recommended_ids)
        except Exception as e:
            import traceback

            print(e, traceback.format_exc())
            return None

    def add_relation(self, relation_type: str, interactor_id: int, interacted_id: int) -> bool:
        return self.cache_manager.add_relation(relation_type, interactor_id, interacted_id)

    def remove_relation(self, relation_type: str, interactor_id: int, interacted_id: int) -> bool:
        return self.cache_manager.rem_relation(relation_type, interactor_id, interacted_id)
