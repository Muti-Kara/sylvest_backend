from django.contrib import admin
from recommender.models import *

admin.site.register(RoledUser)
admin.site.register(Follow)
admin.site.register(UserPostRelation)
admin.site.register(EventAttend)
admin.site.register(CommentLike)
admin.site.register(PostComment)
