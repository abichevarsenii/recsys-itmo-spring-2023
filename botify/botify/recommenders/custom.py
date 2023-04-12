import random

from botify.recommenders.recommender import Recommender
from botify.recommenders.toppop import TopPop

random.seed = 42


class Custom(Recommender):

    def __init__(self, tracks_redis, top_tracks, user_redis, catalog,
                 memory_listened_track_count=20,
                 memory_liked_track_count=10,
                 liked_track_memory_threshold=0.9,
                 liked_track_frequency=0.25,
                 liked_track_threshold=0.5,
                 ):
        self.top_tracks = top_tracks
        self.tracks_redis = tracks_redis
        self.user_redis = user_redis
        self.fallback = TopPop(tracks_redis, top_tracks)
        self.catalog = catalog
        self.memory_listened_track_count = memory_listened_track_count
        self.memory_liked_track_count = memory_liked_track_count
        self.liked_track_memory_threshold = liked_track_memory_threshold
        self.liked_track_frequency = liked_track_frequency
        self.liked_track_threshold = liked_track_threshold

    def recommend_next(self, user: int, prev_track: int, prev_track_time: float) -> int:
        self.catalog.add_listened_track(self.user_redis, user, prev_track, max_size=self.memory_listened_track_count)
        self.catalog.add_liked_track(self.user_redis, user, prev_track, prev_track_time,
                                     max_size=self.memory_liked_track_count,
                                     threshold=self.liked_track_memory_threshold)

        user_data = self.catalog.from_bytes(self.user_redis.get(user))
        if user_data is None:
            return self.fallback.recommend_next(user, prev_track, prev_track_time)

        if prev_track_time <= self.liked_track_threshold and random.random() < self.liked_track_frequency and len(
                user_data.liked_tracks) > 0:
            return random.choice(list(user_data.liked_tracks.keys()))

        recommendations = []
        for liked_track_id in list(user_data.liked_tracks.keys()):
            liked_track_bytes = self.tracks_redis.get(liked_track_id)
            liked_track = self.catalog.from_bytes(liked_track_bytes)
            recommendations.extend(liked_track.recommendations)

        if len(recommendations) == 0:
            return self.fallback.recommend_next(user, prev_track, prev_track_time)

        random.shuffle(recommendations)

        for track in recommendations:
            if track not in user_data.listened_tracks:
                return track

        return recommendations[0]
