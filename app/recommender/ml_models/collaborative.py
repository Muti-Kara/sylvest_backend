from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import pandas as pd
import numpy as np

from recommender.caching.caching import CacheManager

cache_manager = CacheManager()

relations: dict = cache_manager.u2p_to_dict(cache_manager.cache)
df: pd.DataFrame = pd.DataFrame(index=relations["users"], columns=relations["posts"])

for user_id in relations["relations"].keys():
    for post_id in relations["relations"][user_id]:
        df.loc[user_id, post_id] = 1
df = df.fillna(0)

standatized_values: np.ndarray = StandardScaler().fit_transform(df)

pca_obj: PCA = PCA(n_components=5)
pca_data: np.ndarray = pca_obj.fit_transform(standatized_values)
pca_df: np.ndarray = pd.DataFrame(data=pca_data, index=relations["users"])
# print(pca_obj.explained_variance_ratio_)

"""

I should use a kmeans / fcm or t-fcm based model for clustering users.
Afterwards I will create a weighted set for each cluster
and determine weight of each posts by no of user who liked that post in that cluster.

"""

from sklearn.cluster import KMeans

kmeans = KMeans(n_clusters=2)
