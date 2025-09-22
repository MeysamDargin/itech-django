from pymongo import MongoClient
from iTech import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

client = MongoClient(settings.MONGODB_URI)
db = client['iTech']
collection = db['articles']

@csrf_exempt
@require_http_methods(["POST"])
def filter_links(request):
    print("Received request:", request.method, request.path)
    print("Request body:", request.body)
    try:
        # Parse the incoming JSON data
        data = json.loads(request.body)
        
        # If single link object is sent
        if isinstance(data, dict):
            data = [data]
        
        # Get all links from the request
        incoming_links = [item['link'] for item in data]
        
        # Find existing links in MongoDB
        existing_links = collection.find(
            {'link': {'$in': incoming_links}},
            {'link': 1, '_id': 0}
        )
        existing_links = [doc['link'] for doc in existing_links]
        
        # Filter out new links
        new_links = []
        for item in data:
            if item['link'] not in existing_links:
                new_links.append({
                    'link': item['link'],
                    'title': item['title'],
                    'category': item['category']
                })
        
        return JsonResponse({
            'status': 'success',
            'new_links': new_links
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        print("Error:", str(e))
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


