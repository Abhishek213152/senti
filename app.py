from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from googleapiclient.discovery import build
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import urllib.parse

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes


@app.route("/")
def start(): 
    return "Helllo Python"

@app.route('/analyze', methods=['POST'])
def get_comments():
    data = request.get_json()
    VIDEO_URL = data['url']
    API_KEY = 'AIzaSyBLL_Q8VkjEuxRoD9xqePBYaHJc9sZ5qBw'  # Replace with your actual YouTube API key

    # Extract video ID from YouTube video link
    if 'youtu.be' in VIDEO_URL:
        video_id = VIDEO_URL.split('youtu.be/')[1].split('?')[0]
    elif '/watch?v=' in VIDEO_URL:
        video_id = urllib.parse.urlparse(VIDEO_URL).query.split('v=')[1]
    else:
        return jsonify({'error': 'Invalid YouTube video link'}), 400

    youtube = build('youtube', 'v3', developerKey=API_KEY)

    # Fetch video details to get like count and channel ID
    video_response = youtube.videos().list(
        part="snippet, statistics",
        id=video_id
    ).execute()

    if 'items' not in video_response or len(video_response['items']) == 0:
        return jsonify({'error': 'Video not found'}), 404

    video_details = video_response['items'][0]
    video_statistics = video_response['items'][0]['statistics']
    like_count = int(video_statistics.get('likeCount', 0))
    channel_id = video_details['snippet']['channelId']
    channel_name = video_details['snippet']['channelTitle']

    # Fetch channel details to get the profile picture URL
    channel_response = youtube.channels().list(
        part="snippet",
        id=channel_id
    ).execute()

    if 'items' not in channel_response or len(channel_response['items']) == 0:
        return jsonify({'error': 'Channel not found'}), 404

    channel_details = channel_response['items'][0]
    profile_picture_url = channel_details['snippet']['thumbnails']['high']['url']

    # Fetch comments
    organized_comments = []

    def fetch_comments(page_token=None):
        request_params = {
            'part': "snippet",
            'videoId': video_id,
            'textFormat': "plainText",
            'maxResults': 100,
            'pageToken': page_token
        }
        results = youtube.commentThreads().list(**request_params).execute()
        return results

    analyzer = SentimentIntensityAnalyzer()
    total_comments = 0
    positive_comments = 0
    negative_comments = 0
    results = fetch_comments()

    while results:
        for item in results['items']:
            comment = item['snippet']['topLevelComment']['snippet']['textDisplay']
            organized_comments.append(comment)

            sentiment = analyzer.polarity_scores(comment)
            compound_score = sentiment['compound']

            if compound_score >= 0.05:
                positive_comments += 1
            elif compound_score <= -0.05:
                negative_comments += 1

        if 'nextPageToken' in results:
            results = fetch_comments(page_token=results['nextPageToken'])
        else:
            break

    total_comments = len(organized_comments)

    response = {
        'total_comments': total_comments,
        'positive_comments': positive_comments,
        'negative_comments': negative_comments,
        'total_likes': like_count,
        'comments': organized_comments,
        'channel': channel_name,
        'profile_picture_url': profile_picture_url  # Added profile picture URL
    }

    return jsonify(response)


