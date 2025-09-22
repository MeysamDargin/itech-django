from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate, login
from django.core.exceptions import ValidationError
from datetime import datetime
from profiles.models import Profile
from following.models import Follow
from config.mongo_utils import get_collection
import logging

logger = logging.getLogger(__name__)

class UserService:
    @staticmethod
    def create_basic_user(username, email, password):
        if User.objects.filter(username=username).exists():
            raise ValidationError("The username is already taken. Please choose another one.")
        
        if User.objects.filter(email=email).exists():
            raise ValidationError("The email is already registered. Please use a different email.")
        
        user = User.objects.create_user(username=username, email=email, password=password)
        UserService._add_to_free_group(user)
        Profile.objects.create(user=user)
        return user
    
    @staticmethod
    def create_full_user(username, email, password, first_name=None, last_name=None, 
                        address=None, phone_number=None, age=None, profile_image=None):
        if User.objects.filter(username=username).exists():
            raise ValidationError("The username is already taken. Please choose another one.")
        
        if User.objects.filter(email=email).exists():
            raise ValidationError("The email is already registered. Please use a different email.")
        
        if age:
            try:
                birth_date = datetime.strptime(age, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError("Invalid date format. Please use YYYY-MM-DD.")
        
        user = User.objects.create_user(
            username=username,
            email=email, 
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        
        UserService._add_to_free_group(user)
        
        try:
            Profile.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                profile_picture=profile_image,
            )
        except Exception as e:
            user.delete()
            raise ValidationError(f"Failed to create profile: {str(e)}")
        
        return user
    
    @staticmethod
    def _add_to_free_group(user):
        try:
            free_group = Group.objects.get(name='Free')
            user.groups.add(free_group)
        except Group.DoesNotExist:
            free_group = Group.objects.create(name='Free')
            user.groups.add(free_group)
    
    @staticmethod
    def authenticate_and_login(request, username, password):
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return request.session.session_key
        return None
    
    @staticmethod
    def check_username_availability(username):
        return not User.objects.filter(username=username).exists()
    
    @staticmethod
    def check_email_availability(email):
        return not User.objects.filter(email=email).exists()

class ProfileService:
    @staticmethod
    def update_profile(user, data, files):
        profile, created = Profile.objects.get_or_create(user=user)
        updated = False
        
        field_mapping = {
            'first_name': 'first_name',
            'last_name': 'last_name', 
            'job_title': 'job_title',
            'website': 'website',
            'bio': 'bio',
            'phone_number': 'phone_number',
            'country': 'country',
            'city_state': 'city_state',
        }
        
        for field_name, profile_field in field_mapping.items():
            if field_name in data:
                setattr(profile, profile_field, data[field_name])
                updated = True
        
        if 'first_name' in data:
            user.first_name = data['first_name']
        if 'last_name' in data:
            user.last_name = data['last_name']
        if 'username' in data:
            user.username = data['username']
        if 'EmailAddress' in data:
            user.email = data['EmailAddress']
        
        if 'profile_picture' in files:
            profile.profile_picture = files['profile_picture']
            updated = True
        if 'profile_caver' in files:
            profile.profile_caver = files['profile_caver']
            updated = True
        
        if updated:
            profile.save()
            user.save()
        
        return profile
    
    @staticmethod
    def get_user_profile_data(username, requesting_user=None):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise ValidationError("کاربر با این نام کاربری یافت نشد")
        
        try:
            profile = Profile.objects.get(user=user)
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=user)
        
        followers_count = Follow.objects.filter(followed=user).count()
        following_count = Follow.objects.filter(follower=user).count()
        
        is_following = False
        if requesting_user and requesting_user.is_authenticated:
            is_following = Follow.objects.filter(follower=requesting_user, followed=user).exists()
        
        articles = ArticleService.get_user_articles(user.id)
        
        return {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': profile.first_name or user.first_name,
            'last_name': profile.last_name or user.last_name,
            'job_title': profile.job_title,
            'website': profile.website,
            'bio': profile.bio,
            'phone_number': profile.phone_number,
            'country': profile.country,
            'city_state': profile.city_state,
            'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
            'profile_caver': profile.profile_caver.url if profile.profile_caver else None,
            'followers_count': followers_count,
            'following_count': following_count,
            'articles_count': len(articles),
            'articles': articles,
            'is_following': is_following
        }

class ArticleService:
    @staticmethod
    def get_user_articles(user_id):
        articles_users_collection = get_collection('articles_users')
        articles_cursor = articles_users_collection.find({'userId': user_id})
        
        articles = []
        for article in articles_cursor:
            article_data = {
                '_id': str(article['_id']),
                'title': article.get('title', ''),
                'text': article.get('text', ''),
                'imgCover': article.get('imgCover', ''),
                'category': article.get('category', ''),
                'createdAt': article.get('createdAt').isoformat() if article.get('createdAt') else None,
                'updatedAt': article.get('updatedAt').isoformat() if article.get('updatedAt') else None
            }
            articles.append(article_data)
        
        return articles