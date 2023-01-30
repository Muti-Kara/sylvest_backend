from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import linear_kernel, cosine_similarity
import pandas as pd
import numpy as np

from blog.models import MasterPost, Tag
from recommender.preproccess.nlp import process
from recommender.caching.caching import CacheManager
from subjects.models import Profile


class ContentBasedModel:
    def __init__(self):
        self.id_to_index: pd.Series | None = None
        self.index_to_id: pd.Series | None = None
        self.sim_matrix: np.ndarray | None = None
        self.tfdif = TfidfVectorizer(lowercase=False, stop_words=None, token_pattern="(?u)\\b\\w\\w*\\b")
        self.count = CountVectorizer(lowercase=False, stop_words=None, token_pattern="(?u)\\b\\w\\w*\\b")
        self.cache_manager = CacheManager()

    def set_id_index(self, df: pd.DataFrame):
        self.id_to_index = pd.Series(df.index, index=df["id"])
        self.index_to_id = pd.Series(df["id"])

    def cache_to_redis(self, cache_name: str):
        self.cache_manager.cache.delete(f"{cache_name}:")
        for id in self.index_to_id:
            self.cache_manager.add_relation(cache_name, "", id)

    def calculate_similarity_matrix(self):
        raise NotImplementedError()

    def recommend(self, item_id: int):
        index_in_matrix = self.id_to_index[item_id]
        enum = [
            (int(self.index_to_id[item_indice]), float(sim_score))
            for item_indice, sim_score
            in enumerate(self.sim_matrix[index_in_matrix])
        ]
        return dict(enum)


class UserRecommender(ContentBasedModel):
    follow_weight: float = .75
    data_weight: float = .25

    def follows_by_id(self, id: int):
        following_set: set = self.cache_manager.get_relation("follow", id)
        following_set.add("b" + str(id))
        return str(following_set).replace(",", "").replace("'", "").strip("{}")

    @staticmethod
    def __user_serializer(user: Profile) -> dict:
        return {
            'id': user.id,
            'data': f"{user.about if user.about is not None else ''} COMMON{user.id}"
        }

    def calculate_similarity_matrix(self):
        users: list[dict] = [self.__user_serializer(user) for user in Profile.objects.all()]

        df: pd.DataFrame = pd.DataFrame(users)
        self.set_id_index(df)

        df["follows"] = df["id"]
        df["follows"] = df["follows"].apply(self.follows_by_id)

        tfidf_matrix = self.tfdif.fit_transform(df["follows"])
        count_matrix = self.count.fit_transform(df["data"])

        tfidf_matrix = linear_kernel(tfidf_matrix, tfidf_matrix)
        count_matrix = cosine_similarity(count_matrix, count_matrix)

        self.sim_matrix = count_matrix * self.data_weight + tfidf_matrix * self.follow_weight

        self.cache_to_redis("cached_users")


class PostRecommender(ContentBasedModel):
    delay_rate: float = 1.2
    contents_weight: float = .4
    metadata_weight: float = .8

    def calculate_delays(self, df: pd.DataFrame) -> np.ndarray:
        tomorrow = (pd.Timestamp.now() + pd.Timedelta(days=1)).tz_localize("utc")
        df["date"] = tomorrow - df["date"]
        df["date"] = df["date"].apply(lambda x: x.days)
        delay_arr = np.array(df["date"])
        return np.array(list(map(lambda x: self.delay_rate ** x, delay_arr)))

    @staticmethod
    def __stringify_content(content: dict) -> str:
        return str(content).replace("[", " ").replace("]", " ") \
            .replace("{", " ").replace("}", " ") \
            .replace("building_blocks", " ").replace("paragraph", " ")

    def __post_serializer(self, post: MasterPost) -> dict:
        community: str = post.community.title if post.community is not None else ""
        author: str = post.author.username
        tags: str = str(Tag.get_post_tags(post)).replace(",", " ").replace("[", " ").replace("]", " ")

        return {
            'id': post.id,
            'contents': f"{process(self.__stringify_content(post.content))} {post.title} COMMON{post.id}",
            'date': post.date_posted,
            'metadata': f"{author} {community} {process(tags)}"
        }

    def calculate_similarity_matrix(self):
        posts: list[dict] = [self.__post_serializer(post) for post in MasterPost.objects.all()]

        df: pd.DataFrame = pd.DataFrame(posts)
        self.set_id_index(df)

        tfdif_matrix = self.tfdif.fit_transform(df["contents"])
        count_matrix = self.count.fit_transform(df["metadata"])

        tfidf_matrix = linear_kernel(tfdif_matrix, tfdif_matrix)
        count_matrix = cosine_similarity(count_matrix, count_matrix)

        self.sim_matrix = (tfidf_matrix * self.contents_weight + count_matrix * self.metadata_weight) / \
                          self.calculate_delays(df)

        self.cache_to_redis("cached_posts")
