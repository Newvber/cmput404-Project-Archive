# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from django.urls import path
from socialdistribution import views
from django.views.generic import TemplateView

from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', views.FeedPageView.as_view(), name = "feed_page"),

    path("login/", views.LoginPageView.as_view(), name = "login_page"),
    path("signup/", views.SignupPageView.as_view(), name = "signup_page"),
    path("api/login/", views.AuthorLoginAPIView.as_view(), name = "api_author_login"),
    path("api/logout/", views.AuthorLogoutAPIView.as_view(), name = "api_author_logout"),
    path("api/signup/", views.AuthorSignupAPIView.as_view(), name = "api_author_signup"),

    # path('inbox/', views.InboxPageView.as_view(), name='inbox_page'),
    path('api/authors/<path:author_id>/github_update/', views.GitHubUpdateAPIView.as_view(),name='api_github_update'),

    # Inbox API
    path('api/authors/<uuid:author_id>/inbox/', views.InboxAPIView.as_view(), name='inbox-api'),

    # Authors api
    path('api/authors/', views.AuthorsAPIView.as_view(), name='api_authors_list'),

    # Single Author API
    path('api/authors/<uuid:pk>/',views.SingleAuthorAPIView.as_view(),name='api_author_detail'),
    
    # Followers API
    path('api/authors/<uuid:pk>/followers/', views.FollowersListAPIView.as_view(), name='api_author_followers'),
    path('api/authors/<uuid:pk>/followers/<path:fqid>/', views.FollowerDetailAPIView.as_view(), name='api_author_follower_detail'),

    # Entries API
    path("api/authors/<uuid:author_id>/entries/<uuid:entry_id>/image/", views.EntryImageAPIView.as_view(), name="entry-image"),
    path("api/entries/<path:entry_fqid>/image/", views.EntryImageAPIView.as_view(), name="entry-image-global"),
    
    # Comments API
    path('api/authors/<uuid:author_id>/entries/<uuid:entry_id>/comments/', views.CommentsListAPIView.as_view(), name='api_entry_comments'),
    path('api/entries/<path:entry_fqid>/comments/', views.GlobalEntryCommentsAPIView.as_view(), name='api_global_entry_comments'),
    path('api/authors/<uuid:author_id>/entries/<uuid:entry_id>/comment/<path:comment_fqid>/', views.EntryCommentDetailAPIView.as_view(), name='api_entry_comment_detail'),
    path('api/authors/<uuid:author_uuid>/entries/<path:entry_uuid>/commented/', views.CommentAPIView.as_view(), name="api_comment"),
    path('api/authors/<uuid:author_uuid>/entries/<path:entry_uuid>/commented/<uuid:comment_uuid>/', views.CommentAPIView.as_view(), name="comment"),

    # Commented API
    path('api/authors/<uuid:author_id>/commented/', views.AuthorCommentListCreateAPIView.as_view(), name='api_author_commented_list_create'),
    path('api/authors/<path:author_fqid>/commented/', views.AuthorCommentListAPIView.as_view(), name='api_author_commented_list'),
    path('api/authors/<uuid:author_id>/commented/<uuid:comment_id>/', views.AuthorCommentDetailAPIView.as_view(), name='api_author_commented_detail'),
    path('api/commented/<path:comment_fqid>/', views.GlobalCommentDetailAPIView.as_view(), name='api_global_commented_detail'),

    # Likes API
    path('api/authors/<uuid:author_id>/entries/<uuid:entry_id>/comments/<path:comment_fqid>/likes/', views.CommentLikesListAPIView.as_view(), name='api_comment_likes'),
    path('api/authors/<uuid:author_id>/entries/<uuid:entry_id>/likes/', views.EntryLikesListAPIView.as_view(), name='api_entry_likes'),
    path('api/entries/<path:entry_fqid>/likes/', views.GlobalEntryLikesAPIView.as_view(), name='api_global_entry_likes'),

    # Liked API
    path('api/authors/<uuid:author_id>/liked/', views.AuthorLikedListAPIView.as_view(),name='api_author_liked'),
    path('api/authors/<uuid:author_id>/liked/<uuid:like_id>/', views.AuthorLikeDetailAPIView.as_view(), name='api_author_liked_detail'),
    path('api/authors/<path:author_fqid>/liked/', views.GlobalAuthorLikedListAPIView.as_view(), name='api_author_liked_global'),
    path('api/liked/<path:like_fqid>/', views.GlobalLikeDetailAPIView.as_view(),  name='api_global_liked_detail'),
    
    # Other APIs
    path("profile/<path:pk>/relationships/", views.RelationshipsPageView.as_view(), name="relationships_page"),
    # path("authors/<path:pk>/", views.ProfilePageView.as_view(), name = "profile_page"),
    path("api/profile/<path:pk>/stats/", views.ProfileStatsAPIView.as_view(), name="api_profile_stats"),
    path("api/profile/edit/", views.AuthorProfileEditAPIView.as_view(), name="api_profile_edit"),

    path('api/follow/', views.FollowManagerAPIView.as_view(), name = "api_follow"),
    path('api/friends/', views.FriendListAPIView.as_view(), name = "api_friends"),

    #--posting
    path("api/authors/<uuid:author_id>/entries/", views.EntryAPIView.as_view(), name="entry-list-create"),
    path("api/authors/<uuid:author_id>/entries/<uuid:entry_id>/", views.EntryAPIView.as_view(), name="entry-detail"),
    # path("api/entries/<path:entry_id>/", views.EntryAPIView.as_view(), name="entry-detail-global"),
    path("api/entries/<path:entry_fqid>/", views.GlobalEntryDetailAPIView.as_view(), name="api_entry_fqid_detail"),

    path("feed/<path:pk>/newpost/", views.WritePostPageView.as_view(), name="write_post_page"),

    path('api/authors/<uuid:author_id>/entries/<path:entry_id>/like/', views.LikeAPIView.as_view(), name = "like"),
    path('api/authors/<uuid:author_id>/entries/<path:entry_id>/like/<uuid:like_id>/', views.LikeAPIView.as_view(), name = "api_like"),

    path("authors/<uuid:author_id>/entries/<path:entry_id>/edit/", views.EditEntryPageView.as_view(), name="edit_entry_page"),
    path("authors/<uuid:author_id>/entries/<path:entry_id>/", views.EntryDetailPageView.as_view(), name = "entry_page"),
    path("authors/<path:pk>/", views.ProfilePageView.as_view(), name = "profile_page"),
    path('api/authors/<path:fqid>/', views.RemoteSingleAuthorAPIView.as_view(), name='api_author_remote'),

    path("search/authors/", views.AuthorSearchView.as_view(), name="author_search"),
    path("api/author_autocomplete/", views.author_autocomplete, name="author_autocomplete"),
    path("api/sync_remote_authors/", views.sync_remote_authors_view, name="sync_remote_authors"),
]