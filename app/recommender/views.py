from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from django.contrib.auth.models import User

from recommender.recommend import Recommender


@api_view(['GET'])
def update_recommender(request: Request) -> Response:
    user: User = request.user
    # if not user.is_staff:
    #   return Response({'detail': 'unauthorized'}, status=401)
    recommender = Recommender()
    updated: bool = recommender.update_recommender()
    if not updated:
        return Response({'detail': 'recommender cannot be updated at this time'}, status=405)
    return Response({'detail': 'Recommender updated successfully'})

