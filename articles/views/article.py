from django.shortcuts import render
from iTech import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from bson import ObjectId
from config.mongo_utils import get_collection, get_database, insert_document
from django.contrib.auth.decorators import login_required
import os
import datetime
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
from django.contrib.auth.models import User
from profiles.models import Profile
from following.models import Follow
import numpy as np
import re
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils.decorators import method_decorator
from articles.services.services import ArticleService, SaveService
from articles.serializers.serializers import (
    FilterLinksSerializer, ArticleListSerializer, ToggleLikeSerializer,
    ArticleDetailSerializer, CreateArticleSerializer, UpdateArticleSerializer,
    TrackReadSerializer, UploadImageSerializer, CreateSaveDirectorySerializer,
    SaveDirectorySerializer, ToggleSaveSerializer, SavedItemSerializer,
    CheckSavedSerializer, UpdateSaveDirectorySerializer, TimeBasedArticleSerializer
)
from articles.utils.article_utils import get_absolute_img_cover_url

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()

# Initialize services
article_service = ArticleService()
save_service = SaveService()

class FilterLinksAPIView(APIView):
    @method_decorator(csrf_exempt)
    def post(self, request):
        try:
            data = json.loads(request.body)
            if isinstance(data, dict):
                data = [data]
            
            serializer = FilterLinksSerializer(data=data, many=True)
            if not serializer.is_valid():
                return Response({
                    'status': 'error',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            new_links = article_service.filter_new_links(serializer.validated_data)
            
            return Response({
                'status': 'success',
                'new_links': new_links
            })
        except json.JSONDecodeError:
            return Response({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in filter_links: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RecommendedArticlesListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    @method_decorator(csrf_exempt)
    def get(self, request):
        try:
            articles = article_service.get_recommended_articles(user_id=request.user.id)
            serializer = ArticleListSerializer(articles, many=True)
            return Response({
                'status': 'success',
                'articles': serializer.data
            })
        except Exception as e:
            logger.error(f"Error in get_articles: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BreakingArticlesListAPIView(APIView):
    @method_decorator(csrf_exempt)
    def get(self, request):
        try:
            articles = article_service.get_all_articles()
            serializer = ArticleListSerializer(articles, many=True)
            return Response({
                'status': 'success',
                'articles': serializer.data
            })
        except Exception as e:
            logger.error(f"Error in get_articles: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ToggleArticleLikeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def post(self, request, article_id):
        if not ObjectId.is_valid(article_id):
            return Response({
                'status': 'error',
                'message': 'Invalid article ID format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            response_data, status_code = article_service.toggle_like(article_id, request.user.id, request)
            serializer = ToggleLikeSerializer(response_data)
            return Response(serializer.data, status=status_code)
        except Exception as e:
            logger.error(f"Error in toggle_article_like: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ArticleDetailAPIView(APIView):
    @method_decorator(csrf_exempt)
    def get(self, request, article_id):
        if not ObjectId.is_valid(article_id):
            return Response({
                'status': 'error',
                'message': 'Invalid article ID format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_id = request.user.id if request.user.is_authenticated else None
            article_data, found = article_service.get_article_by_id(article_id, user_id)
            
            if not found:
                return Response({
                    'status': 'error',
                    'message': 'Article not found in any collection'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = ArticleDetailSerializer(article_data)
            print(serializer)
            return Response({
                'status': 'success',
                'article': serializer.data
            })
        except Exception as e:
            logger.error(f"Error in get_article_detail: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CreateArticleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def post(self, request):
        try:
            serializer = CreateArticleSerializer(data=request.data)
            if serializer.is_valid():
                article_data = serializer.validated_data
                article_data['imgCover'] = request.FILES.get('imgCover')
                response_data, status_code = article_service.create_article(article_data, request.user.id, request)
                return Response(response_data, status=status_code)
            else:
                return Response({
                    'status': 'error',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in create_article: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UpdateArticleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def post(self, request, article_id):
        if not ObjectId.is_valid(article_id):
            return Response({
                'status': 'error',
                'message': 'Invalid article ID format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            serializer = UpdateArticleSerializer(data=request.data)
            if serializer.is_valid():
                update_data = serializer.validated_data
                if 'imgCover' in request.FILES:
                    update_data['imgCover'] = request.FILES['imgCover']
                response_data, status_code = article_service.update_article(article_id, update_data, request.user.id)
                return Response(response_data, status=status_code)
            else:
                return Response({
                    'status': 'error',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in update_article: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UploadImageForArticleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def post(self, request):
        try:
            serializer = UploadImageSerializer(data=request.data)
            if serializer.is_valid():
                image_file = serializer.validated_data['image']
                current_date = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"upload_{current_date}_{image_file.name}"
                path = os.path.join('uploaded_images', filename)
                saved_path = default_storage.save(path, ContentFile(image_file.read()))
                image_url = request.build_absolute_uri(f"{settings.MEDIA_URL}{saved_path}")
                return Response({
                    'status': 'success',
                    'message': 'Image uploaded successfully',
                    'image_url': image_url
                })
            else:
                return Response({
                    'status': 'error',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in upload_image_for_article: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeleteArticleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def post(self, request, article_id):
        if not ObjectId.is_valid(article_id):
            return Response({
                'status': 'error',
                'message': 'Invalid article ID format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            response_data, status_code = article_service.delete_article(article_id, request.user.id)
            return Response(response_data, status=status_code)
        except Exception as e:
            logger.error(f"Error in delete_article: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TrackArticleReadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def post(self, request):
        try:
            serializer = TrackReadSerializer(data=request.POST)
            if serializer.is_valid():
                read_data = serializer.validated_data
                read_data['user_id'] = request.user.id
                response_data, status_code = article_service.track_article_read(read_data)
                return Response(response_data, status=status_code)
            else:
                return Response({
                    'status': 'error',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in track_article_read: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CreateSaveDirectoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def post(self, request):
        try:
            serializer = CreateSaveDirectorySerializer(data=request.POST)
            if serializer.is_valid():
                response_data, status_code = save_service.create_directory(serializer.validated_data['name'], request.user.id)
                return Response(response_data, status=status_code)
            else:
                return Response({
                    'status': 'error',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in create_save_directory: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SaveDirectoriesListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def get(self, request):
        try:
            directories = save_service.get_directories(request.user.id)
            serializer = SaveDirectorySerializer(directories, many=True)
            return Response({
                'status': 'success',
                'directories': serializer.data
            })
        except Exception as e:
            logger.error(f"Error in get_save_directories: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ToggleArticleSavedAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def post(self, request, article_id):
        if not ObjectId.is_valid(article_id):
            return Response({
                'status': 'error',
                'message': 'Invalid article ID format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            serializer = ToggleSaveSerializer(data=request.POST)
            if serializer.is_valid():
                directory_id = serializer.validated_data.get('directoryId')
                response_data, status_code = save_service.toggle_save(article_id, request.user.id, directory_id)
                return Response(response_data, status=status_code)
            else:
                return Response({
                    'status': 'error',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in toggle_article_saved: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SavedArticlesListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def get(self, request):
        try:
            saved_items = save_service.get_saved_articles(request.user.id)
            serializer = SavedItemSerializer(saved_items, many=True)
            return Response({
                'status': 'success',
                'saved_items': serializer.data
            })
        except Exception as e:
            logger.error(f"Error in get_saved_articles: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CheckArticleSavedAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def get(self, request, article_id):
        if not ObjectId.is_valid(article_id):
            return Response({
                'status': 'error',
                'message': 'Invalid article ID format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            response_data = save_service.check_saved(article_id, request.user.id)
            serializer = CheckSavedSerializer(response_data)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error in check_article_saved: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DeleteSaveDirectoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def post(self, request, directory_id):
        if not ObjectId.is_valid(directory_id):
            return Response({
                'status': 'error',
                'message': 'Invalid directory ID format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            response_data, status_code = save_service.delete_directory(directory_id, request.user.id)
            return Response(response_data, status=status_code)
        except Exception as e:
            logger.error(f"Error in delete_save_directory: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UpdateSaveDirectoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def post(self, request, directory_id):
        if not ObjectId.is_valid(directory_id):
            return Response({
                'status': 'error',
                'message': 'Invalid directory ID format'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            serializer = UpdateSaveDirectorySerializer(data=request.POST)
            if serializer.is_valid():
                response_data, status_code = save_service.update_directory(directory_id, serializer.validated_data['name'], request.user.id)
                return Response(response_data, status=status_code)
            else:
                return Response({
                    'status': 'error',
                    'message': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error in update_save_directory: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MorningArticlesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def get(self, request):
        try:
            articles = article_service.get_time_based_articles(request.user.id, request, 12, 24)
            serializer = TimeBasedArticleSerializer(articles, many=True)
            return Response({
                "status": "success",
                "articles": serializer.data
            })
        except Exception as e:
            logger.error(f"Error in MorningArticlesAPIView: {str(e)}")
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AfternoonArticlesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def get(self, request):
        try:
            articles = article_service.get_time_based_articles(request.user.id, request, 12, 24)
            serializer = TimeBasedArticleSerializer(articles, many=True)
            return Response({
                "status": "success",
                "articles": serializer.data
            })
        except Exception as e:
            logger.error(f"Error in AfternoonArticlesAPIView: {str(e)}")
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class NightArticlesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def get(self, request):
        try:
            articles = article_service.get_time_based_articles(request.user.id, request, 12, 72)
            serializer = TimeBasedArticleSerializer(articles, many=True)
            return Response({
                "status": "success",
                "articles": serializer.data
            })
        except Exception as e:
            logger.error(f"Error in NightArticlesAPIView: {str(e)}")
            return Response({
                "status": "error",
                "message": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)