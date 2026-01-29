# SocialDistribution REST API Reference

## Overview
This documentation outlines the structure, purpose, and usage of each endpoint available in the system. It is intended for developers who wish to integrate, extend, or consume the backend services of the SocialDistribution platform, either locally or across federated nodes.

All endpoints follow REST principles, using JSON as the standard data exchange format. Authentication is handled via session or token-based methods, depending on the $$

use case.

The API supports the following key functionalities:
- Authentication APIs
- Author APIs
- Follow / Friend APIs
- Entry APIs
- Comment APIs
- Like APIs
- Inbox API
- Extras

<br><br><br>









# Authentication APIs

## /api/signup/

Creates a new author account.<br>
The username must be unique and is used for login.<br>
If the registration is successful, a new author profile is created and returned.<br>
If the username is already taken, a 400 Bad Request is returned with an appropriate error message<br>
The author must be approved by an admin through the admin panel before being able to log in again in the future.<br>

### Endpoint: POST /api/signup

### Request:
```json
{
  "username": "user1",
  "display_name": "user1",
  "password": "12345678"
}
```

### Successful Response: '201 CREATED'
```json
{
    "id": "6f61fa90-ff70-442d-98c6-1f6155212dfb",
    "username": "user1",
    "display_name": "john doe",
    "message": "Your account was created and is awaiting approval by the admin."
}
```

### - When you try to sign up using the same username -

### Error Response (username already exists): '400 Bad Request'
```json
{
  "username": [
    "Author with this username already exists."
  ]
}
```
<br><br><br>





## /api/login/

Authenticates an existing author using username and password. If credentials are valid and the user is not already logged in, the session is established and the author’s basic info is returned.

### Endpoint: POST /api/login

### Request:
```json
{
  "username": "user1",
  "password": "12345678"
}
```

### Successful Response: '200 OK'
```json
{
  "id": "6f61fa90-ff70-442d-98c6-1f6155212dfb",
  "username": "user1",
  "display_name": "user1"
}
```

<!-- *** YOU MUST use api/logout to log out before sending the same query *** -->
<!-- *** otherwise, you would get *** -->

<!-- Error response: '400 Bad Request'
'''json
{
    "error": "Already logged in."
} -->

Returned when the provided username or password is incorrect.<br>
### Error response: '401 Unauthorized'
```json
{
    "error": "Invalid credentials"
}
```

Returned when the user hasn't been approved by admin.<br>
### Error response: '403 Forbidden'
```json
{
    "error": "Your account is not approved yet. Please wait for admin approval."
}
```
<br><br><br>




## api/logout/

Logs out the currently authenticated author by terminating their session.
This endpoint requires the user to be authenticated (i.e., already logged in).
If the logout is successful, a confirmation message is returned.
This API can be safely called multiple times regardless of login state.
Even if the user is not logged in, the server will still respond with a
success message, as the end result. The server does not need to validate
any username in the request, IT SIMPLY INVALIDATES the session or token associated
with the request, completing the logout process securely and consistently.

### Endpoint: POST /api/logout

### Request:
```json
{
  "username": "user1"
}
```

### Successful Response: '200 OK'
```json
{
  "message": "Logged out successfully."
}
```

<br><br><br><br><br>











# Author APIs

## /api/authors/&lt;uuid:pk&gt;/

Fetches the profile details of a specific author identified by their UUID (pk).

### Endpoint: GET /api/authors/&lt;uuid:pk&gt;/

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
{
    "type": "author",
    "id": "http://localhost:8000/api/authors/246a6a7f-6100-497e-a317-fc81b05c95e6/",
    "host": "http://localhost:8000",
    "displayName": "user1",
    "github": "",
    "profileImage": "",
    "web": "http://localhost:8000/authors/user1/",
    "description": "This is your profile description. You can describe yourself here in a few sentences."
}
```

<br>
When a wrong uuid is provided

### Error Response: '404 Not Found'
```json
{
    "detail": "No Author matches the given query."
}
```

<br><br><br>





## /api/authors/

Returns a list of all authors registered in the system.<br>
This endpoint allows clients to fetch a paginated list of author profiles.<br>

This endpoint supports ***pagination*** using the following query parameters:

Examples: <br>
	•	Get the first page (default size): <br>
GET /api/authors/<br>
	•	Get page 4 (default size):<br>
GET /api/authors/?page=4<br>
	•	Get page 4 with 40 authors per page:<br>
GET /api/authors/?page=4&size=40<br>

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
{
    "type": "authors",
    "authors": [
        {
            "type": "author",
            "id": "http://localhost:8000/api/authors/14267dd2-f9f1-46ff-920c-f26552af95bb/",
            "host": "http://localhost:8000",
            "displayName": "user11",
            "github": "",
            "profileImage": "",
            "web": "http://localhost:8000/authors/user11/",
            "description": null
        },
        {
            "type": "author",
            "id": "http://localhost:8000/api/authors/1b5f3829-49ae-4bd5-8249-3110b7457d32/",
            "host": "http://localhost:8000",
            "displayName": "user30",
            "github": "",
            "profileImage": "",
            "web": "http://localhost:8000/authors/user30/",
            "description": null
        },
        ...
    ]
}
```

<br><br><br>

## /api/authors/<path:fqid>/

Retrieves a single author by fqid

This is a simple GET request — no request body is required.

### Endpoint: GET /api/authors/<path:fqid>/

Successful Response: '200 OK'
```json
{
    "type": "author",
    "uid": "6defd15a-6de6-4988-b24d-c0d9c4861720",
    "id": "https://p5-white-c051cd6cf6a3.herokuapp.com/api/authors/6defd15a-6de6-4988-b24d-c0d9c4861720",
    "username": "veryuniquename",
    "displayName": "veryuniquename",
    "github": "",
    "profileImage": "",
    "web": "https://p5-white-c051cd6cf6a3.herokuapp.com/authors/profile/6defd15a-6de6-4988-b24d-c0d9c4861720",
    "host": "https://p5-white-c051cd6cf6a3.herokuapp.com/api/",
    "is_active": true,
    "is_staff": false,
    "is_superuser": false,
    "description": ""
}
```

<br><br><br>



## /api/profile/edit/

This endpoint allows an authenticated user to edit their own profile information, such as display_name, username, password, github_link, or description.<br>

Edits a single profile field (display_name, username, password, or github_link) of the currently authenticated author. <br>
Only one field may be updated per request.<br>
This endpoint requires the user to be authenticated.<br>

Validation includes:<br>
    - Value can't be empty<br>
    - New value must differ from the current one<br>
    - username and display_name must be unique and within max length<br>
    - password must be 8 - 16 characters<br>
    - PASSWORD CHANGE LOGS THE USER OUT IMMEDIATELY.<br>

### Endpoint: PATCH /api/profile/edit/

When no authentication credentials provided

### Error Response: '403 Forbidden'
```json
{
    "detail": "Authentication credentials were not provided."
}
```


Assuming that user is authenticated
### Request:
```json
{
  "username": "new_username"
}
```

### Successful Response: '200 OK'
```json
{
  "username": "new_username"
}
```



When attempting to change the username to the current username

### Error Response (username already exists): '400 Bad Request'
```json
{
    "error": "username is unchanged."
}
```

PASSWORD CHANGE LOGS THE USER OUT IMMEDIATELY
```json
{
  "password": "new_password"
}
```

### Successful Response: '200 OK'
```json
{
    "message": "Password updated."
}
```

<br><br><br>




## /api/profile/<author_uuid>/stats/

Retrieves public statistics for a given author's profile<br>
This includes the number of users following the author, and the number<br>
of users the author is following.<br>

This is a simple GET request — no request body is required.

### Endpoint: GET /api/profile/<author_uuid>/stats/

Successful Response: '200 OK'
```json
{
  "follower_count": 14,
  "following_count": 10
}
```

<br><br><br>


## /api/authors/<uuid:author_id>/github_update/

Retrieves entries from github automatically <br>
MUST LINK ur github account before updating <br>

### Endpoint: POST /api/authors/<uuid:author_id>/github_update/

Assuming github link connected to whatever https://github.com/Newvber

## Request:
```json
{}
```

### Successful Response: '201 CREATED'
```json
{
    "detail": "9 new entries created"
}
```

If there is nothing to be updated
### Successful Response: '200 OK'
```json
{
    "detail": "No entry needed to update"
}
```

<br><br><br><br><br>








# Follow / Friend APIs

## /api/follow

Manages the follow relationship between two authors.<br>
This endpoint handles follow requests, accepting follow requests, and rejecting/canceling them.
All actions require authentication.<br>
Authors can follow others, accept incoming follow requests, or delete pending/existing relationships.<br>

Endpoint: <br>
GET /api/follow/?author=<author_uuid> -> gets all the follow requests <br>
POST /api/follow/ -> send follow request (DEPRECATED) <br>
PATCH /api/follow/ -> accept a request <br>
DELETE /api/follow/ -> delete/reject/cancel request <br>

*** Assuming that the user is authenticated ***

## FOR FEDERATION (migrate -> /api/inbox)
## Endpoint: GET /api/follow/?author=<author_uuid>
Successful Response: '200 OK'

```json
[
    {
        "type": "follow",
        "summary": "http://localhost:8000/api/authors/6e4b96c1-50ab-48e4-91aa-8276c417f290/ wants to follow you.",
        "actor": {
            "id": "http://localhost:8000/api/authors/6e4b96c1-50ab-48e4-91aa-8276c417f290/"
        },
        "object": "http://localhost:8000/api/authors/246a6a7f-6100-497e-a317-fc81b05c95e6/"
    },
    {
        "type": "follow",
        "summary": "http://localhost:8000/api/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/ wants to follow you.",
        "actor": {
            "id": "http://localhost:8000/api/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/"
        },
        "object": "http://localhost:8000/api/authors/246a6a7f-6100-497e-a317-fc81b05c95e6/"
    },
    ...
]
```

<!-- *** NEED TO FIX author1 -> author1 being accepted *** -->
<!-- *** NEED TO FIX when author 1 logged in, and author 10 -> author 15 goes through *** -->

## THIS IS OLD, follow POST requests are all being handled by api/inbox
## Endpoint: POST /api/follow/

## Request:
```json
{
  "from_author": "user1_uuid",
  "to_author": "user2_uuid"
}
```

## Successful Response: '201 Created'
```json
{
  "id": 969,
  "from_author": "user1_uuid",
  "to_author": "user2_uuid",
  "pending": true,
  "accepted": false
  "created_at": "2025-06-19T07:15:55.355981Z"
}
```

*** If request already exists: ***

## Error response: '400 Bad Request'
```json
{
    "non_field_errors": [
        "The fields from_author, to_author must make a unique set."
    ]
}
```



## Endpoint: PATCH /api/follow/

ASSUMING AUTHOR A -> AUTHOR B FOLLOW REQUEST SENT

## Request:
```json
{
  "from_author": "user1_uuid",
  "to_author": "user2_uuid"
}
```

## Successful Response: '200 OK'
```json
{
    "type": "follow",
    "summary": "http://localhost:8000/api/authors/246a6a7f-6100-497e-a317-fc81b05c95e6/ wants to follow you.",
    "actor": {
        "id": "http://localhost:8000/api/authors/246a6a7f-6100-497e-a317-fc81b05c95e6/"
    },
    "object": "http://localhost:8000/api/authors/3f4ed01e-2047-4856-bcde-e6075bb1fb92/"
}
```

*** PENDING and ACCEPTED CHANGED ***
*** AS LONG AS THE FOLLOW REQUEST EXISTS IN DATABASE ***
*** WHEN YOU SEND THE SAME PATCH REQUEST OVER AND OVER, IT GIVES YOU THE SAME RESPONSE ***

## REQUEST:
```json
{
  "from_author": "random_uuid1",
  "to_author": "random_uuid2"
}
```

## Error



Endpoint: DELETE /api/follow/
ASSUMING THE FOLLOWING REQUEST EXISTS IN DATABASE<br>
THIS CAN BE USED TO EITHER REJECT or UNFOLLOW<br>

curl -X DELETE http://localhost:8000/api/follow/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: gKjwZ7xgTqstSVDtgTv5pINfDR97Lwg6" \
  -H "Cookie: csrftoken=gKjwZ7xgTqstSVDtgTv5pINfDR97Lwg6; sessionid=vdbl5zxqeyvo9eyfj7x6raquoq5dsdny" \
  -d '{
    "from_author": "uuid1",
    "to_author": "uuid2"
}'

WE OBTAIN "DELETE /api/follow/ HTTP/1.1" 204 0

HOWEVER IF THE REQUEST DOESN'T EXIST
WE OBTAIN "DELETE /api/follow/ HTTP/1.1" 404

```json
{
  "detail": "Not found."
}
```

<br><br><br>





## api/friends/ 

Check and Manage Mutual Friendships between Authors. <br>
Two authors are considered friends if they both follow each other (mutual follow). <br>

## Endpoint: GET /api/friends/?author=<author_uuid>

Successful Response: '200 OK'
```json
[
    {
        "id": "uuid523",
        "username": "user39"
    },
    {
        "id": "uuid124",
        "username": "user22"
    },
    {
        "id": "uuid124",
        "username": "user36"
    },
    {
        "id": "uuid124",
        "username": "user35"
    }
]
```

<br><br><br>



## /api/authors/&lt;uuid:pk&gt;/followers/

Retrieves the list of followers for the author with the specified UUID.

This is a simple GET request — no request body is required.

### Endpoint: GET /api/authors/<author_uuid>/followers/


### Successful Response: '200 OK'
```json
{
    "type": "followers",
    "followers": [
        {
            "type": "author",
            "id": "http://localhost:8000/api/authors/6e4b96c1-50ab-48e4-91aa-8276c417f290/",
            "host": "http://localhost:8000",
            "displayName": "user2",
            "github": "",
            "profileImage": "",
            "web": "http://localhost:8000/authors/user2/",
            "description": null
        },
        {
            "type": "author",
            "id": "http://localhost:8000/api/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/",
            "host": "http://localhost:8000",
            "displayName": "user3",
            "github": "",
            "profileImage": "",
            "web": "http://localhost:8000/authors/user3/",
            "description": null
        },
        ...
    ]
}
```

<br><br><br>



## api/authors/<uuid:pk>/followers/<path:fqid>

This endpoint checks whether a specific author (fqid) is following another author (pk).

This is a simple GET request — no request body is required.

### Endpoint: GET /api/authors/<uuid:pk>/followers/<path:fqid>

### Successful Response: '200 OK'
```json
{
    "type": "author",
    "id": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/d72a66c0-09bf-4dd4-affc-99f3fd6433ed/",
    "host": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/",
    "displayName": "jayinqiao",
    "github": "",
    "profileImage": "",
    "web": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/authors/jayinqiao/",
    "description": null
}
```



<br><br><br><br><br>







# Entry APIs
## /api/entries/<path:entry_fqid>/

An API endpoint that retrieves a remote entry’s information based on its percent-encoded Fully Qualified ID (FQID).

This is a simple GET request — no request body is required.

### Endpoint: GET /api/entries/<path:entry_fqid>/

### Successful Response: '200 OK'
```json
{
    "type": "entry",
    "title": "so TIRED",
    "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com//api/authors/840ea125-e252-4313-9246-c271f1858609/entries/af0f9ea4-5f00-4300-b5b0-9ae77338680b",
    "web": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/authors/840ea125-e252-4313-9246-c271f1858609/entries/https%3A%2F%2Fsocialdistribution-olive-jay-e7737313c8b5.herokuapp.com%2F%2Fapi%2Fauthors%2F840ea125-e252-4313-9246-c271f1858609%2Fentries%2Faf0f9ea4-5f00-4300-b5b0-9ae77338680b/",
    "description": "so TIRED",
    "contentType": "text/plain",
    "content": "so TIRED",
    "author": {
        "type": "author",
        "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/",
        "host": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/",
        "displayName": "",
        "github": "",
        "profileImage": "",
        "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/authors/840ea125-e252-4313-9246-c271f1858609/",
        "description": null
    },
    "comments": {
        "type": "comments",
        "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/authors/840ea125-e252-4313-9246-c271f1858609/entries/https%3A%2F%2Fsocialdistribution-olive-jay-e7737313c8b5.herokuapp.com%2F%2Fapi%2Fauthors%2F840ea125-e252-4313-9246-c271f1858609%2Fentries%2Faf0f9ea4-5f00-4300-b5b0-9ae77338680b/",
        "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/entries/https%3A%2F%2Fsocialdistribution-olive-jay-e7737313c8b5.herokuapp.com%2F%2Fapi%2Fauthors%2F840ea125-e252-4313-9246-c271f1858609%2Fentries%2Faf0f9ea4-5f00-4300-b5b0-9ae77338680b/comments/",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    },
    "likes": {
        "type": "likes",
        "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/authors/840ea125-e252-4313-9246-c271f1858609/entries/https%3A%2F%2Fsocialdistribution-olive-jay-e7737313c8b5.herokuapp.com%2F%2Fapi%2Fauthors%2F840ea125-e252-4313-9246-c271f1858609%2Fentries%2Faf0f9ea4-5f00-4300-b5b0-9ae77338680b/",
        "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/entries/https%3A%2F%2Fsocialdistribution-olive-jay-e7737313c8b5.herokuapp.com%2F%2Fapi%2Fauthors%2F840ea125-e252-4313-9246-c271f1858609%2Fentries%2Faf0f9ea4-5f00-4300-b5b0-9ae77338680b/likes/",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    },
    "published": "2025-07-24T11:38:39-0600",
    "visibility": "PUBLIC"
}
```

<br><br><br>





<br><br><br>



## /api/authors/<uuid:author_id>/entries/

Retrieves all entries authored by a specific user, or allows the authenticated user to create a new one.

### Endpoint: GET /api/authors/<uuid:author_id>/entries/

### Successful Response: '200 OK'
```json
[
    {
        "type": "entry",
        "title": "another post by user3 (public)",
        "id": "http://localhost:8000/api/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/5a2f86b0-3a2d-4151-8c39-b39a45839317",
        "web": "http://localhost:8000/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/5a2f86b0-3a2d-4151-8c39-b39a45839317",
        "description": "another post by user3 (public)",
        "contentType": "text/plain",
        "content": "hello",
        "author": {
            "type": "author",
            "id": "http://localhost:8000/api/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/",
            "host": "http://localhost:8000",
            "displayName": "user3",
            "github": "",
            "profileImage": "",
            "web": "http://localhost:8000/authors/user3/",
            "description": null
        },
        "comments": {
            "type": "comments",
            "web": "http://localhost:8000/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/5a2f86b0-3a2d-4151-8c39-b39a45839317",
            "id": "http://localhost:8000/api/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/5a2f86b0-3a2d-4151-8c39-b39a45839317/comment/",
            "page_number": 1,
            "size": 5,
            "count": 0,
            "src": []
        },
        "likes": {
            "type": "likes",
            "web": "http://localhost:8000/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/5a2f86b0-3a2d-4151-8c39-b39a45839317",
            "id": "http://localhost:8000/api/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/5a2f86b0-3a2d-4151-8c39-b39a45839317/likes/",
            "page_number": 1,
            "size": 5,
            "count": 0,
            "src": []
        },
        "published": "2025-07-10T01:49:46-0600",
        "visibility": "PUBLIC"
    },
    ...
]
```
<br>

### Endpoint: POST /api/authors/<uuid:author_id>/entries/

### Request:
```json
{
    "title": "posting an entry using django framework thingy..",
    "content": "ugh... so tired.",
    "description": "posting an entry using django framework thingy..",
    "visibility": "PUBLIC",
    "contentType": "text/plain"
}
```

### Successful Resopnse: '201 CREATED'
```json
{
    "type": "entry",
    "title": "posting an entry using django framework thingy..",
    "id": "http://localhost:8000/api/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/0c084dcf-c1c0-46d8-a7a8-c4d8a47237ab",
    "web": "http://localhost:8000/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/0c084dcf-c1c0-46d8-a7a8-c4d8a47237ab",
    "description": "posting an entry using django framework thingy..",
    "contentType": "text/plain",
    "content": "ugh... so tired.",
    "author": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/",
        "host": "http://localhost:8000",
        "displayName": "user3",
        "github": "",
        "profileImage": "",
        "web": "http://localhost:8000/authors/user3/",
        "description": null
    },
    "comments": {
        "type": "comments",
        "web": "http://localhost:8000/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/0c084dcf-c1c0-46d8-a7a8-c4d8a47237ab",
        "id": "http://localhost:8000/api/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/0c084dcf-c1c0-46d8-a7a8-c4d8a47237ab/comment/",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    },
    "likes": {
        "type": "likes",
        "web": "http://localhost:8000/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/0c084dcf-c1c0-46d8-a7a8-c4d8a47237ab",
        "id": "http://localhost:8000/api/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/0c084dcf-c1c0-46d8-a7a8-c4d8a47237ab/likes/",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    },
    "published": "2025-07-10T01:51:56-0600",
    "visibility": "PUBLIC"
}
```

# PATCH method, and POSTing IMAGES, MARKDOWN work similarly too.

<br><br><br>



## /api/authors/<uuid:author_id>/entries/<path:entry_id>/image/

Retrieves the image associated with the specified entry. This endpoint is used to fetch the image content of an image-only post.

### Endpoint: GET /api/authors/<uuid:author_id>/entries/<path:entry_id>/image/

This is a simple GET request — no request body is required.

### Successful Response**: `200 OK' 
## Returns a raw image file


<br><br><br>


## api/entries/<path:entry_fqid>/image/

Retrieves the image associated with the specified entry_fqid. This endpoint is used to fetch the image content of an image-only post.

### Endpoint: GET /api/entries/<path:entry_fqid>/image/

This is a simple GET request — no request body is required.

### Successful Response**: `200 OK' 
## Returns a raw image file

<br><br><br>


## /api/authors/<uuid:author_id>/entries/<uuid:entry_id>/

Retrieves a single post (entry) created by a specific author. <br>
This is used to fetch detailed information about a specific entry, such as its content, type, author, comments, and visibility. <br>
Also, we can use PATCH to edit a specific entry. <br>

### Endpoint: GET /api/authors/<uuid:author_id>/entries/<uuid:entry_id>/


### Successful Response: '200 OK'
```json
{
    "type": "entry",
    "title": "user 12's first public post!",
    "id": "http://localhost:8000/api/authors/ca526556-da91-43ce-a663-b9d7226e1933/entries/1312c9a4-36af-4408-8835-c1179acd1d29",
    "web": "http://localhost:8000/authors/ca526556-da91-43ce-a663-b9d7226e1933/entries/1312c9a4-36af-4408-8835-c1179acd1d29",
    "description": "user 12's first public post!",
    "contentType": "text/plain",
    "content": "this is my first public post.",
    "author": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/ca526556-da91-43ce-a663-b9d7226e1933/",
        "host": "http://localhost:8000",
        "displayName": "user12",
        "github": "",
        "profileImage": "",
        "web": "http://localhost:8000/authors/user12/",
        "description": null
    },
    "comments": {
        "type": "comments",
        "web": "http://localhost:8000/authors/ca526556-da91-43ce-a663-b9d7226e1933/entries/1312c9a4-36af-4408-8835-c1179acd1d29",
        "id": "http://localhost:8000/api/authors/ca526556-da91-43ce-a663-b9d7226e1933/entries/1312c9a4-36af-4408-8835-c1179acd1d29/comment/",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    },
    "likes": {
        "type": "likes",
        "web": "http://localhost:8000/authors/ca526556-da91-43ce-a663-b9d7226e1933/entries/1312c9a4-36af-4408-8835-c1179acd1d29",
        "id": "http://localhost:8000/api/authors/ca526556-da91-43ce-a663-b9d7226e1933/entries/1312c9a4-36af-4408-8835-c1179acd1d29/likes/",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    },
    "published": "2025-07-10T00:37:43-0600",
    "visibility": "PUBLIC"
}
```

<br>

### Endpoint: PATCH /api/authors/<uuid:author_id>/entries/<uuid:entry_id>/
### Request:
```json
{
    "title": "editing my entry",
    "content": "ugh... so tired.",
    "description": "editing my entry",
    "visibility": "PUBLIC",
    "contentType": "text/plain"
}
```

### Successful Response: '200 OK'
```json
{
    "type": "entry",
    "title": "editing my entry",
    "id": "http://localhost:8000/api/authors/ca526556-da91-43ce-a663-b9d7226e1933/entries/1312c9a4-36af-4408-8835-c1179acd1d29",
    "web": "http://localhost:8000/authors/ca526556-da91-43ce-a663-b9d7226e1933/entries/1312c9a4-36af-4408-8835-c1179acd1d29",
    "description": "editing my entry",
    "contentType": "text/plain",
    "content": "ugh... so tired.",
    "author": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/ca526556-da91-43ce-a663-b9d7226e1933/",
        "host": "http://localhost:8000",
        "displayName": "user12",
        "github": "",
        "profileImage": "",
        "web": "http://localhost:8000/authors/user12/",
        "description": null
    },
    "comments": {
        "type": "comments",
        "web": "http://localhost:8000/authors/ca526556-da91-43ce-a663-b9d7226e1933/entries/1312c9a4-36af-4408-8835-c1179acd1d29",
        "id": "http://localhost:8000/api/authors/ca526556-da91-43ce-a663-b9d7226e1933/entries/1312c9a4-36af-4408-8835-c1179acd1d29/comment/",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    },
    "likes": {
        "type": "likes",
        "web": "http://localhost:8000/authors/ca526556-da91-43ce-a663-b9d7226e1933/entries/1312c9a4-36af-4408-8835-c1179acd1d29",
        "id": "http://localhost:8000/api/authors/ca526556-da91-43ce-a663-b9d7226e1933/entries/1312c9a4-36af-4408-8835-c1179acd1d29/likes/",
        "page_number": 1,
        "size": 5,
        "count": 1,
        "src": [
            {
                "type": "like",
                "author": {
                    "type": "author",
                    "id": "http://localhost:8000/api/authors/ca526556-da91-43ce-a663-b9d7226e1933/",
                    "host": "http://localhost:8000",
                    "displayName": "user12",
                    "github": "",
                    "profileImage": "",
                    "web": "http://localhost:8000/authors/user12/",
                    "description": null
                },
                "published": "2025-07-10T08:52:58.861629+00:00",
                "id": "http://localhost:8000/api/authors/ca526556-da91-43ce-a663-b9d7226e1933/liked/45ae4d34-6c40-4f07-952a-39340b10ad4f",
                "object": "http://localhost:8000/authors/ca526556-da91-43ce-a663-b9d7226e1933/entries/1312c9a4-36af-4408-8835-c1179acd1d29"
            }
        ]
    },
    "published": "2025-07-10T00:37:43-0600",
    "visibility": "PUBLIC"
}
```

<br><br><br>

<br><br><br><br><br>












# Comment APIs

## /api/authors/<uuid:author_id>/entries/<path:entry_id>/comments/

Retrieves all comments associated with a specific post (entry) made by a given author.

### Endpoint: GET /api/authors/<uuid:author_id>/entries/<path:entry_id>/comments/

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
{
    "type": "comments",
    "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/ee1faa30-a518-440e-9118-b3d841df11e9/comments/",
    "web": "http://localhost:8000/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/ee1faa30-a518-440e-9118-b3d841df11e9/",
    "page_number": 1,
    "size": 5,
    "count": 2,
    "src": [
        {
            "type": "comment",
            "author": {
                "type": "author",
                "id": "http://localhost:8000/api/authors/71a08d92-e6b0-414f-a8ed-a2dd825e43b9/",
                "host": "http://localhost:8000",
                "displayName": "user4",
                "github": "",
                "profileImage": "",
                "web": "http://localhost:8000/authors/user4/",
                "description": null
            },
            "comment": "testing comments..",
            "contentType": "text/plain",
            "published": "2025-07-10T03:03:30-0600",
            "id": "http://localhost:8000/api/authors/71a08d92-e6b0-414f-a8ed-a2dd825e43b9/commented/74bd3918-f2da-416b-aafd-644af111d3bd",
            "entry": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/ee1faa30-a518-440e-9118-b3d841df11e9",
            "likes": {
                "type": "likes",
                "web": "http://localhost:8000/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/ee1faa30-a518-440e-9118-b3d841df11e9",
                "id": "http://localhost:8000/api/authors/71a08d92-e6b0-414f-a8ed-a2dd825e43b9/commented/74bd3918-f2da-416b-aafd-644af111d3bd/likes",
                "page_number": 1,
                "size": 5,
                "count": 0,
                "src": []
            }
        },
        ...
    ]
}
```

<br><br><br>


## api/entries/<path:entry_fqid>/comments/

Retrieves all comments associated with a specific post (by fqid).

### Endpoint: GET api/entries/<path:entry_fqid>/comments/

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
{
    "type": "comments",
    "id": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/9d682b1d-5dac-45cf-a022-c4efecf6d02b/comments/",
    "web": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/9d682b1d-5dac-45cf-a022-c4efecf6d02b/",
    "page_number": 1,
    "size": 5,
    "count": 2,
    "src": [
        {
            "type": "comment",
            "author": {
                "type": "author",
                "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/",
                "host": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/",
                "displayName": "",
                "github": "",
                "profileImage": "",
                "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/authors/840ea125-e252-4313-9246-c271f1858609/",
                "description": null
            },
            "comment": "fqid comment testttt",
            "contentType": "text/plain",
            "published": "2025-07-24T12:25:25-0600",
            "id": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/commented/ade3485f-e04b-482e-bc67-e3e6ccb0f523",
            "entry": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/9d682b1d-5dac-45cf-a022-c4efecf6d02b",
            "likes": {
                "type": "likes",
                "web": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/9d682b1d-5dac-45cf-a022-c4efecf6d02b/",
                "id": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/9d682b1d-5dac-45cf-a022-c4efecf6d02b/comments/https%3A%2F%2Fqz-socialdistribution-528b041fc34f.herokuapp.com%2Fapi%2Fauthors%2F840ea125-e252-4313-9246-c271f1858609%2Fcommented%2Fade3485f-e04b-482e-bc67-e3e6ccb0f523/likes/",
                "page_number": 1,
                "size": 5,
                "count": 0,
                "src": []
            }
        },
        {
            "type": "comment",
            "author": {
                "type": "author",
                "id": "http://localhost:8000/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/",
                "host": "http://localhost:8000",
                "displayName": "",
                "github": "",
                "profileImage": "",
                "web": "http://localhost:8000/authors/admin/",
                "description": null
            },
            "comment": "fqid comment test",
            "contentType": "text/plain",
            "published": "2025-07-24T12:25:16-0600",
            "id": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/commented/1187c699-011d-44d6-afc9-ee92523a3a8d",
            "entry": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/9d682b1d-5dac-45cf-a022-c4efecf6d02b",
            "likes": {
                "type": "likes",
                "web": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/9d682b1d-5dac-45cf-a022-c4efecf6d02b/",
                "id": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/9d682b1d-5dac-45cf-a022-c4efecf6d02b/comments/https%3A%2F%2Fqz-socialdistribution-528b041fc34f.herokuapp.com%2Fapi%2Fauthors%2F658c372a-36c9-4f74-b31e-0f7b62ae0baf%2Fcommented%2F1187c699-011d-44d6-afc9-ee92523a3a8d/likes/",
                "page_number": 1,
                "size": 5,
                "count": 0,
                "src": []
            }
        }
    ]
}
```

<br><br><br>

## api/authors/<uuid:author_id>/entries/<path:entry_id>/comment/<path:comment_fqid>/

allows accessing a specific comment (comment_fqid) on a specific post (entry_id) belonging to a specific author (author_id).

### Endpoint: GET api/authors/<uuid:author_id>/entries/<path:entry_id>/comment/<path:comment_fqid>/

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
{
    "type": "comment",
    "author": {
        "type": "author",
        "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/",
        "host": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/",
        "displayName": "",
        "github": "",
        "profileImage": "",
        "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/authors/admin/",
        "description": null
    },
    "comment": "dddd",
    "contentType": "text/plain",
    "published": "2025-07-24T12:38:33-0600",
    "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/commented/654552b3-6d48-4a1b-b0a2-45f6e35c59b3",
    "entry": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/2f9257aa-0cf3-4577-9f82-4b17bcd88165",
    "likes": {
        "type": "likes",
        "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com//authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/https%3A%2F%2Fqz-socialdistribution-528b041fc34f.herokuapp.com%2Fapi%2Fauthors%2F658c372a-36c9-4f74-b31e-0f7b62ae0baf%2Fentries%2F2f9257aa-0cf3-4577-9f82-4b17bcd88165/",
        "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com//api/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/https%3A%2F%2Fqz-socialdistribution-528b041fc34f.herokuapp.com%2Fapi%2Fauthors%2F658c372a-36c9-4f74-b31e-0f7b62ae0baf%2Fentries%2F2f9257aa-0cf3-4577-9f82-4b17bcd88165/comments/https%3A%2F%2Fsocialdistribution-olive-jay-e7737313c8b5.herokuapp.com%2Fapi%2Fauthors%2F840ea125-e252-4313-9246-c271f1858609%2Fcommented%2F654552b3-6d48-4a1b-b0a2-45f6e35c59b3/likes/",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    }
}
```


<br><br><br>


## /api/authors/<uuid:author_id>/commented/

Returns a list of entries (posts) that the specified author has commented on. <br>
This endpoint is used to track where the author has left comments. <br>

### Endpoint: GET /api/authors/<uuid:author_id>/commented/

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
{
    "type": "comments",
    "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/commented/",
    "page_number": 1,
    "size": 5,
    "count": 3,
    "src": [
        {
            "type": "comment",
            "author": {
                "type": "author",
                "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/",
                "host": "http://localhost:8000",
                "displayName": "user5",
                "github": "",
                "profileImage": "",
                "web": "http://localhost:8000/authors/user5/",
                "description": null
            },
            "comment": "1234",
            "contentType": "text/plain",
            "published": "2025-07-10T03:17:11-0600",
            "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/commented/b85b99bf-79cf-42ae-a8c0-8db23afa3b50",
            "entry": "http://localhost:8000/api/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/http://localhost:8000/api/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/0c084dcf-c1c0-46d8-a7a8-c4d8a47237ab",
            "likes": {
                "type": "likes",
                "web": "http://localhost:8000/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/http://localhost:8000/api/authors/9062d7d4-1ba3-478b-9e9c-8f961b0dff04/entries/0c084dcf-c1c0-46d8-a7a8-c4d8a47237ab",
                "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/commented/b85b99bf-79cf-42ae-a8c0-8db23afa3b50/likes",
                "page_number": 1,
                "size": 5,
                "count": 0,
                "src": []
            }
        },
        ...
    ]
}
```

<br><br><br>




## /api/authors/<uuid:author_id>/commented/<uuid:comment_id>/

Retrieves a specific comment written by the specified author.

### Endpoint: GET /api/authors/<uuid:author_id>/commented/<uuid:comment_id>/

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
{
    "type": "comment",
    "author": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/",
        "host": "http://localhost:8000",
        "displayName": "user5",
        "github": "",
        "profileImage": "",
        "web": "http://localhost:8000/authors/user5/",
        "description": null
    },
    "comment": "this is my post.",
    "contentType": "text/plain",
    "published": "2025-07-10T03:03:18-0600",
    "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/commented/b5d2e8ce-bb72-4585-ae53-fed60d43a86d",
    "entry": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/ee1faa30-a518-440e-9118-b3d841df11e9",
    "likes": {
        "type": "likes",
        "web": "http://localhost:8000/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/ee1faa30-a518-440e-9118-b3d841df11e9",
        "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/commented/b5d2e8ce-bb72-4585-ae53-fed60d43a86d/likes",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    }
}
```

<br><br><br>





## /api/authors/<uuid:author_uuid>/entries/<path:entry_uuid>/commented/
# Refer to /api/authors/<uuid:author_uuid>/entries/<path:entry_uuid>/comments/ <br>
# The only difference is that ~/comments/ has pagination data enclosing comments jsons

<br><br><br>




## api/authors/<uuid:author_uuid>/entries/<path:entry_uuid>/commented/<uuid:comment_uuid>/

Retrieves a specific comment that the given author posted on a specific entry.

### Endpoint: GET api/authors/<uuid:author_uuid>/entries/<path:entry_uuid>/commented/<uuid:comment_uuid>/

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
{
    "type": "comment",
    "author": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/",
        "host": "http://localhost:8000",
        "displayName": "user5",
        "github": "",
        "profileImage": "",
        "web": "http://localhost:8000/authors/user5/",
        "description": null
    },
    "comment": "this is my post.",
    "contentType": "text/plain",
    "published": "2025-07-10T03:03:18-0600",
    "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/commented/b5d2e8ce-bb72-4585-ae53-fed60d43a86d",
    "entry": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/ee1faa30-a518-440e-9118-b3d841df11e9",
    "likes": {
        "type": "likes",
        "web": "http://localhost:8000/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/entries/ee1faa30-a518-440e-9118-b3d841df11e9",
        "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/commented/b5d2e8ce-bb72-4585-ae53-fed60d43a86d/likes",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    }
}
```

# we could potentially use api/authors/<uuid:author_id>/commented/<uuid:comment_id>/

<br><br><br>



## api/authors/<path:author_fqid>/commented/

returns a list of all comments made by the specified author (author_fqid), whether they were posted on local or remote posts.

### Endpoint: GET api/authors/<path:author_fqid>/commented/

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
[
    {
        "type": "comment",
        "author": {
            "type": "author",
            "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/",
            "host": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/",
            "displayName": "",
            "github": "",
            "profileImage": "",
            "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/authors/admin/",
            "description": null
        },
        "comment": "dddd",
        "contentType": "text/plain",
        "published": "2025-07-24T12:38:33-0600",
        "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/commented/654552b3-6d48-4a1b-b0a2-45f6e35c59b3",
        "entry": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/2f9257aa-0cf3-4577-9f82-4b17bcd88165",
        "likes": {
            "type": "likes",
            "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com//authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/https%3A%2F%2Fqz-socialdistribution-528b041fc34f.herokuapp.com%2Fapi%2Fauthors%2F658c372a-36c9-4f74-b31e-0f7b62ae0baf%2Fentries%2F2f9257aa-0cf3-4577-9f82-4b17bcd88165/",
            "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com//api/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/https%3A%2F%2Fqz-socialdistribution-528b041fc34f.herokuapp.com%2Fapi%2Fauthors%2F658c372a-36c9-4f74-b31e-0f7b62ae0baf%2Fentries%2F2f9257aa-0cf3-4577-9f82-4b17bcd88165/comments/https%3A%2F%2Fsocialdistribution-olive-jay-e7737313c8b5.herokuapp.com%2Fapi%2Fauthors%2F840ea125-e252-4313-9246-c271f1858609%2Fcommented%2F654552b3-6d48-4a1b-b0a2-45f6e35c59b3/likes/",
            "page_number": 1,
            "size": 5,
            "count": 0,
            "src": []
        }
    },
    {
        "type": "comment",
        "author": {
            "type": "author",
            "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/",
            "host": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/",
            "displayName": "",
            "github": "",
            "profileImage": "",
            "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/authors/admin/",
            "description": null
        },
        "comment": "fff",
        "contentType": "text/plain",
        "published": "2025-07-24T12:38:12-0600",
        "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/commented/d7e6de08-8625-4863-ba65-f12132e67f84",
        "entry": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/9d682b1d-5dac-45cf-a022-c4efecf6d02b",
        "likes": {
            "type": "likes",
            "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com//authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/https%3A%2F%2Fqz-socialdistribution-528b041fc34f.herokuapp.com%2Fapi%2Fauthors%2F658c372a-36c9-4f74-b31e-0f7b62ae0baf%2Fentries%2F9d682b1d-5dac-45cf-a022-c4efecf6d02b/",
            "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com//api/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/https%3A%2F%2Fqz-socialdistribution-528b041fc34f.herokuapp.com%2Fapi%2Fauthors%2F658c372a-36c9-4f74-b31e-0f7b62ae0baf%2Fentries%2F9d682b1d-5dac-45cf-a022-c4efecf6d02b/comments/https%3A%2F%2Fsocialdistribution-olive-jay-e7737313c8b5.herokuapp.com%2Fapi%2Fauthors%2F840ea125-e252-4313-9246-c271f1858609%2Fcommented%2Fd7e6de08-8625-4863-ba65-f12132e67f84/likes/",
            "page_number": 1,
            "size": 5,
            "count": 0,
            "src": []
        }
    },
    ...
]
```

<br><br><br>

## api/commented/<path:comment_fqid>/

retrieves or manages a specific comment identified by its full ID (comment_fqid)

### Endpoint: GET api/commented/<path:comment_fqid>/

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
{
    "type": "comment",
    "author": {
        "type": "author",
        "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/",
        "host": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/",
        "displayName": "",
        "github": "",
        "profileImage": "",
        "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/authors/admin/",
        "description": null
    },
    "comment": "fff",
    "contentType": "text/plain",
    "published": "2025-07-24T12:38:12-0600",
    "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/commented/d7e6de08-8625-4863-ba65-f12132e67f84",
    "entry": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/9d682b1d-5dac-45cf-a022-c4efecf6d02b",
    "likes": {
        "type": "likes",
        "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com//authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/https%3A%2F%2Fqz-socialdistribution-528b041fc34f.herokuapp.com%2Fapi%2Fauthors%2F658c372a-36c9-4f74-b31e-0f7b62ae0baf%2Fentries%2F9d682b1d-5dac-45cf-a022-c4efecf6d02b/",
        "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com//api/authors/658c372a-36c9-4f74-b31e-0f7b62ae0baf/entries/https%3A%2F%2Fqz-socialdistribution-528b041fc34f.herokuapp.com%2Fapi%2Fauthors%2F658c372a-36c9-4f74-b31e-0f7b62ae0baf%2Fentries%2F9d682b1d-5dac-45cf-a022-c4efecf6d02b/comments/https%3A%2F%2Fsocialdistribution-olive-jay-e7737313c8b5.herokuapp.com%2Fapi%2Fauthors%2F840ea125-e252-4313-9246-c271f1858609%2Fcommented%2Fd7e6de08-8625-4863-ba65-f12132e67f84/likes/",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    }
}
```


<br><br><br><br><br>












# Like APIs

## /api/authors/<uuid:author_id>/liked/

Returns a list of all objects that the specified author has liked. <br>
This includes entries, comments. <br>

### Endpoint: GET /api/authors/<uuid:author_id>/liked/

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
{
    "type": "likes",
    "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/liked/",
    "web": "http://localhost:8000/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/liked/",
    "page_number": 1,
    "size": 50,
    "count": 4,
    "src": [
        {
            "type": "like",
            "author": {
                "type": "author",
                "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7",
                "host": "http://localhost:8000/api/",
                "displayName": "user5",
                "github": "",
                "profileImage": "",
                "web": "http://localhost:8000/authors/49284c63-bdfd-4c13-8902-e52588e11ec7"
            },
            "published": "2025-07-10T09:44:19.427741+00:00",
            "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/liked/d5ae6bcc-d1bd-434f-bb04-3ad80b3b6de2",
            "object": "http://localhost:8000/api/authors/71a08d92-e6b0-414f-a8ed-a2dd825e43b9/commented/74bd3918-f2da-416b-aafd-644af111d3bd"
        },
        ...
    ]
}
```

<br><br><br>



## /api/authors/<uuid:author_id>/liked/<uuid:like_id>/

Retrieves a specific “like” object made by a given author.

### Endpoint: GET /api/authors/<uuid:author_id>/liked/<uuid:like_id>/

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
{
    "type": "like",
    "author": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7",
        "host": "http://localhost:8000/api/",
        "displayName": "user5",
        "github": "",
        "profileImage": "",
        "web": "http://localhost:8000/authors/49284c63-bdfd-4c13-8902-e52588e11ec7"
    },
    "published": "2025-07-10T09:44:19.427741+00:00",
    "id": "http://localhost:8000/api/authors/49284c63-bdfd-4c13-8902-e52588e11ec7/liked/d5ae6bcc-d1bd-434f-bb04-3ad80b3b6de2",
    "object": "http://localhost:8000/api/authors/71a08d92-e6b0-414f-a8ed-a2dd825e43b9/commented/74bd3918-f2da-416b-aafd-644af111d3bd"
}
```

<br><br><br>

## /api/authors/<path:author_fqid>/liked/

Retrieves "like" objects made by a given user (author_fqid)

### Endpoint: GET /api/authors/<path:author_fqid>/liked/

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
{
    "type": "likes",
    "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/liked/",
    "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/liked/",
    "page_number": 1,
    "size": 50,
    "count": 2,
    "src": [
        {
            "type": "like",
            "author": {
                "type": "author",
                "id": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416",
                "host": "http://localhost:8000/api/",
                "displayName": "user1",
                "github": "",
                "profileImage": "",
                "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/authors/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2Fac29708b-0f0f-41bb-90e0-5f91e2c73416/"
            },
            "published": "2025-08-07T18:04:42.048419+00:00",
            "id": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/liked/eab67b30-b54c-4dc2-a1d9-69c72f242b17",
            "object": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/entries/a405aa94-b1b3-4530-b3cf-ad6150d6924a"
        },
        {
            "type": "like",
            "author": {
                "type": "author",
                "id": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416",
                "host": "http://localhost:8000/api/",
                "displayName": "user1",
                "github": "",
                "profileImage": "",
                "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/authors/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2Fac29708b-0f0f-41bb-90e0-5f91e2c73416/"
            },
            "published": "2025-08-07T17:39:53.551571+00:00",
            "id": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/liked/364d3a3b-7e96-477b-94e2-451adc23d4cf",
            "object": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/entries/53027755933"
        }
    ]
}
```

<br><br><br>

## /api/liked/<path:like_fqid>

Retrieves a "like" object by a given like_fqid

### Endpoint: GET /api/liked/<path:like_fqid>

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
{
    "type": "like",
    "author": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416",
        "host": "http://localhost:8000/api/",
        "displayName": "user1",
        "github": "",
        "profileImage": "",
        "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/authors/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2Fac29708b-0f0f-41bb-90e0-5f91e2c73416/"
    },
    "published": "2025-08-07T18:04:42.048419+00:00",
    "id": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/liked/eab67b30-b54c-4dc2-a1d9-69c72f242b17",
    "object": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/entries/a405aa94-b1b3-4530-b3cf-ad6150d6924a"
}
```

<br><br><br>


## api/entries/<path:entry_fqid>/likes/

Retrieves like objects related to an entry (by fqid).

### Endpoint: GET api/entries/<path:entry_fqid>/likes/

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json
{
    "type": "likes",
    "id": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/d72a66c0-09bf-4dd4-affc-99f3fd6433ed/entries/d8d173d6-161f-4f01-9d3f-26aafa21f30c/likes/",
    "web": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/authors/d72a66c0-09bf-4dd4-affc-99f3fd6433ed/entries/d8d173d6-161f-4f01-9d3f-26aafa21f30c/",
    "page_number": 1,
    "size": 50,
    "count": 2,
    "src": [
        {
            "type": "like",
            "author": {
                "type": "author",
                "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609",
                "host": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api",
                "displayName": "",
                "github": "",
                "profileImage": ""
            },
            "published": "2025-07-24T19:04:02.816105+00:00",
            "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/liked/2f1e7620-926e-4f08-94f9-458172f8d515",
            "object": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/d72a66c0-09bf-4dd4-affc-99f3fd6433ed/entries/d8d173d6-161f-4f01-9d3f-26aafa21f30c"
        },
        {
            "type": "like",
            "author": {
                "type": "author",
                "id": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/d72a66c0-09bf-4dd4-affc-99f3fd6433ed",
                "host": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api",
                "displayName": "jayinqiao",
                "github": "",
                "profileImage": ""
            },
            "published": "2025-07-24T19:01:42.696261+00:00",
            "id": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/d72a66c0-09bf-4dd4-affc-99f3fd6433ed/liked/0584f984-c1e1-4843-ac71-2f80a3e182af",
            "object": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/d72a66c0-09bf-4dd4-affc-99f3fd6433ed/entries/d8d173d6-161f-4f01-9d3f-26aafa21f30c"
        }
    ]
}
```


## api/authors/<uuid:author_id>/entries/<uuid:entry_id>/likes/

returns a list of likes on a specific post (entry_id) authored by the given author (author_id).

### Endpoint: GET api/entries/<path:entry_fqid>/likes/

This is a simple GET request — no request body is required.
### Successful Response: '200 OK'
```json
{
    "type": "likes",
    "id": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/entries/a405aa94-b1b3-4530-b3cf-ad6150d6924a/likes/",
    "web": "http://localhost:8000/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/entries/a405aa94-b1b3-4530-b3cf-ad6150d6924a/",
    "page_number": 1,
    "size": 50,
    "count": 1,
    "src": [
        {
            "type": "like",
            "author": {
                "type": "author",
                "id": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416",
                "host": "http://localhost:8000/api/",
                "displayName": "user1",
                "github": "https://github.com/samsung",
                "profileImage": "",
                "web": "http://localhost:8000/authors/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2Fac29708b-0f0f-41bb-90e0-5f91e2c73416/"
            },
            "published": "2025-08-07T18:04:38.110068+00:00",
            "id": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/liked/eab67b30-b54c-4dc2-a1d9-69c72f242b17",
            "object": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/entries/a405aa94-b1b3-4530-b3cf-ad6150d6924a"
        }
    ],
    ...
}
```

<br><br><br>





## api/authors/<uuid:author_id>/entries/<path:entry_id>/comments/<path:comment_fqid>/likes/

returns a list of likes on a specific comment (comment_fqid) that was posted on a specific post (entry_id) owned by a given author (author_id).

### Endpoint: GET api/authors/<uuid:author_id>/entries/<path:entry_id>/comments/<path:comment_fqid>/likes/

https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/entries/https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com//api/authors/840ea125-e252-4313-9246-c271f1858609/entries/ba69fb20-8ff5-4191-a9aa-26164c04f569/comments/https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/commented/2dbdb91d-0854-40f3-afdf-db13c43193fc/likes/

This is a simple GET request — no request body is required.

### Successful Response: '200 OK'
```json

{
    "type": "likes",
    "web": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/authors/840ea125-e252-4313-9246-c271f1858609/entries/https%3A%2F%2Fsocialdistribution-olive-jay-e7737313c8b5.herokuapp.com%2F%2Fapi%2Fauthors%2F840ea125-e252-4313-9246-c271f1858609%2Fentries%2Fba69fb20-8ff5-4191-a9aa-26164c04f569/",
    "id": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/entries/https%3A%2F%2Fsocialdistribution-olive-jay-e7737313c8b5.herokuapp.com%2F%2Fapi%2Fauthors%2F840ea125-e252-4313-9246-c271f1858609%2Fentries%2Fba69fb20-8ff5-4191-a9aa-26164c04f569/comments/https%3A%2F%2Fqz-socialdistribution-528b041fc34f.herokuapp.com%2Fapi%2Fauthors%2F840ea125-e252-4313-9246-c271f1858609%2Fcommented%2F2dbdb91d-0854-40f3-afdf-db13c43193fc/likes/",
    "page_number": 1,
    "size": 5,
    "count": 1,
    "src": [
        {
            "type": "like",
            "author": {
                "type": "author",
                "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/",
                "host": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/",
                "displayName": "",
                "github": "",
                "profileImage": "",
                "web": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/authors/840ea125-e252-4313-9246-c271f1858609/",
                "description": null
            },
            "published": "2025-07-24T19:14:43.261973+00:00",
            "id": "https://socialdistribution-olive-jay-e7737313c8b5.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/liked/87d80aae-d931-4134-8f49-f9e1e67f13de",
            "object": "https://qz-socialdistribution-528b041fc34f.herokuapp.com/api/authors/840ea125-e252-4313-9246-c271f1858609/commented/2dbdb91d-0854-40f3-afdf-db13c43193fc"
        }
    ]
}
```

## DEPRECATED -> use inbox
api/authors/<uuid:author_id>/entries/<path:entry_id>/like/
api/authors/<uuid:author_id>/entries/<path:entry_id>/like/<uuid:like_id>/




<br><br><br><br><br>








# Inbox API

## /api/authors/<uuid:author_id>/inbox/

Sends an activity (such as follow request, like, comment) to the inbox of the specified author.

### Endpoint: POST /api/authors/<uuid:author_id>/inbox/

### Request:
```json
{
    "type": "like",
    "author": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416",
        "host": "http://localhost:8000/api/",
        "displayName": "user1",
        "github": "https://github.com/samsung",
        "profileImage": "",
        "web": "http://localhost:8000/authors/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2Fac29708b-0f0f-41bb-90e0-5f91e2c73416/"
    },
    "object": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/entries/53027755933",
    "published": "2025-08-07T03:43:31.257Z",
    "id": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/liked/364d3a3b-7e96-477b-94e2-451adc23d4cf"
}
```

### Successful Response: '201 CREATED'
```json
{
    "type": "like",
    "author": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416",
        "host": "http://localhost:8000/api/",
        "displayName": "user1",
        "github": "https://github.com/samsung",
        "profileImage": "",
        "web": "http://localhost:8000/authors/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2Fac29708b-0f0f-41bb-90e0-5f91e2c73416/"
    },
    "published": "2025-08-07T03:45:08.083642+00:00",
    "id": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/liked/364d3a3b-7e96-477b-94e2-451adc23d4cf",
    "object": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416/entries/53027755933"
}
```

<br><br><br>

### Request:
```json
{
    "type": "follow",
    "summary": "user2 wants to follow user1",
    "actor": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/716e8e72-1416-4e62-b408-84e582ccb8ab",
        "host": "http://localhost:8000/api/",
        "displayName": "user2",
        "github": "",
        "profileImage": "",
        "web": "http://localhost:8000/authors/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2F716e8e72-1416-4e62-b408-84e582ccb8ab/"
    },
    "object": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/ac29708b-0f0f-41bb-90e0-5f91e2c73416",
        "host": "http://localhost:8000/api/",
        "displayName": "user1",
        "github": "https://github.com/samsung",
        "profileImage": "",
        "web": "http://localhost:8000/authors/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2Fac29708b-0f0f-41bb-90e0-5f91e2c73416/"
    }
}
```

### Successful Response: '201 CREATED'
```json
{
    "type": "follow",
    "summary": "user2 wants to follow user1",
    "actor": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/716e8e72-1416-4e62-b408-84e582ccb8ab",
        "host": "http://localhost:8000/api/",
        "displayName": "user2",
        "github": "",
        "profileImage": "",
        "web": "http://localhost:8000/authors/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2F716e8e72-1416-4e62-b408-84e582ccb8ab/"
    },
    "object": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/716e8e72-1416-4e62-b408-84e582ccb8ab",
        "host": "http://localhost:8000/api/",
        "displayName": "user1",
        "github": "https://github.com/samsung",
        "profileImage": "",
        "web": "http://localhost:8000/authors/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2Fac29708b-0f0f-41bb-90e0-5f91e2c73416/"
    }
}
```




<br><br><br>

### Request:
```json
{
    "type": "comment",
    "author": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/716e8e72-1416-4e62-b408-84e582ccb8ab",
        "host": "http://localhost:8000/api/",
        "displayName": "user2",
        "github": "",
        "profileImage": "",
        "web": "http://localhost:8000/authors/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2F716e8e72-1416-4e62-b408-84e582ccb8ab/"
    },
    "comment": "123",
    "contentType": "text/plain",
    "published": "2025-08-06T21:50:07-0600",
    "id": "http://localhost:8000/api/authors/716e8e72-1416-4e62-b408-84e582ccb8ab/commented/642991db-0ac7-4c77-bdbc-c642f9fcf0a6",
    "entry": "http://localhost:8000/api/authors/716e8e72-1416-4e62-b408-84e582ccb8ab/entries/d706eb7f-c87c-4f4a-9bc5-b293bd894d49",
    "likes": {
        "type": "likes",
        "web": "http://localhost:8000/authors/716e8e72-1416-4e62-b408-84e582ccb8ab/entries/d706eb7f-c87c-4f4a-9bc5-b293bd894d49/",
        "id": "http://localhost:8000/api/authors/716e8e72-1416-4e62-b408-84e582ccb8ab/entries/d706eb7f-c87c-4f4a-9bc5-b293bd894d49/comments/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2F716e8e72-1416-4e62-b408-84e582ccb8ab%2Fcommented%2F642991db-0ac7-4c77-bdbc-c642f9fcf0a6/likes/",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    }
}
```

### Successful Response: '201 CREATED'
```json
{
    "type": "comment",
    "author": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/716e8e72-1416-4e62-b408-84e582ccb8ab",
        "host": "http://localhost:8000/api/",
        "displayName": "user2",
        "github": "",
        "profileImage": "",
        "web": "http://localhost:8000/authors/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2F716e8e72-1416-4e62-b408-84e582ccb8ab/"
    },
    "comment": "123",
    "contentType": "text/plain",
    "published": "2025-08-06T21:51:45-0600",
    "id": "http://localhost:8000/api/authors/716e8e72-1416-4e62-b408-84e582ccb8ab/commented/642991db-0ac7-4c77-bdbc-c642f9fcf0a6",
    "entry": "http://localhost:8000/api/authors/716e8e72-1416-4e62-b408-84e582ccb8ab/entries/d706eb7f-c87c-4f4a-9bc5-b293bd894d49",
    "likes": {
        "type": "likes",
        "web": "http://localhost:8000/authors/716e8e72-1416-4e62-b408-84e582ccb8ab/entries/d706eb7f-c87c-4f4a-9bc5-b293bd894d49/",
        "id": "http://localhost:8000/api/authors/716e8e72-1416-4e62-b408-84e582ccb8ab/entries/d706eb7f-c87c-4f4a-9bc5-b293bd894d49/comments/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2F716e8e72-1416-4e62-b408-84e582ccb8ab%2Fcommented%2F642991db-0ac7-4c77-bdbc-c642f9fcf0a6/likes/",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    }
}
```

<br><br><br>

### Successful Response: '200 OK'
```json
{
    "type": "entry",
    "title": "editing using django",
    "id": "http://localhost:8000/api/authors/6e4b96c1-50ab-48e4-91aa-8276c417f290/entries/66d1b3cd-6f60-49a7-93c7-d4091d3edc6e",
    "web": "http://localhost:8000/authors/6e4b96c1-50ab-48e4-91aa-8276c417f290/entries/66d1b3cd-6f60-49a7-93c7-d4091d3edc6e",
    "description": "editing using django",
    "contentType": "text/plain",
    "content": "F*CK",
    "author": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/6e4b96c1-50ab-48e4-91aa-8276c417f290/",
        "host": "http://localhost:8000",
        "displayName": "user2",
        "github": "",
        "profileImage": "",
        "web": "http://localhost:8000/authors/user2/",
        "description": null
    },
    "published": "2025-07-24T11:38:39-0600",
    "visibility": "PUBLIC"
}
```

### Successful Response: '201 CREATED'
```json
{
    "type": "entry",
    "title": "editing using django",
    "id": "http://localhost:8000/api/authors/6e4b96c1-50ab-48e4-91aa-8276c417f290/entries/66d1b3cd-6f60-49a7-93c7-d4091d3edc6e",
    "web": "http://localhost:8000/authors/6e4b96c1-50ab-48e4-91aa-8276c417f290/entries/66d1b3cd-6f60-49a7-93c7-d4091d3edc6e/",
    "description": "editing using django",
    "contentType": "text/plain",
    "content": "F*CK",
    "author": {
        "type": "author",
        "id": "http://localhost:8000/api/authors/6e4b96c1-50ab-48e4-91aa-8276c417f290",
        "host": "http://localhost:8000/api/",
        "displayName": "user2",
        "github": "",
        "profileImage": "",
        "web": "http://localhost:8000/authors/http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauthors%2F6e4b96c1-50ab-48e4-91aa-8276c417f290/"
    },
    "comments": {
        "type": "comments",
        "web": "http://localhost:8000/authors/6e4b96c1-50ab-48e4-91aa-8276c417f290/entries/66d1b3cd-6f60-49a7-93c7-d4091d3edc6e/",
        "id": "http://localhost:8000/api/authors/6e4b96c1-50ab-48e4-91aa-8276c417f290/entries/66d1b3cd-6f60-49a7-93c7-d4091d3edc6e/comments",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    },
    "likes": {
        "type": "likes",
        "web": "http://localhost:8000/authors/6e4b96c1-50ab-48e4-91aa-8276c417f290/entries/66d1b3cd-6f60-49a7-93c7-d4091d3edc6e/",
        "id": "http://localhost:8000/api/authors/6e4b96c1-50ab-48e4-91aa-8276c417f290/entries/66d1b3cd-6f60-49a7-93c7-d4091d3edc6e/likes",
        "page_number": 1,
        "size": 5,
        "count": 0,
        "src": []
    },
    "published": "2025-07-24T11:38:39-0600",
    "visibility": "PUBLIC"
}
```


<br><br><br><br><br>

# Extras

## /api/author_autocomplete

This is a simple GET request — no request body is required.

This endpoint provides autocomplete suggestions for authors based on a partial search query. <br>
It accepts a query string parameter q, performs a case-insensitive match on display_name, <br>
and returns up to 5 matching authors. <br>

Query Parameter: <br>
	•	q: Partial name to search for <br>

### Endpoint: GET /api/author_autocomplete

### Example: GET /api/author_autocomplete/?q=a

### Response

```json
{
  "results": [
    {
      "id": "http://localhost:8000/api/authors/73f0e85b-d1e2-4b0e-a808-bd6d71d313c7",
      "display_name": "janedoe"
    },
    {
      "id": "http://localhost:8000/api/authors/b32d7bda-ded5-415e-80a4-e89c1309c94f",
      "display_name": "randomuser"
    },
    {
      "id": "http://localhost:8000/api/authors/bed8086f-7bd0-4ecf-b380-b933a6a08c5e",
      "display_name": "samsung"
    },
    {
      "id": "http://localhost:8000/api/authors/557ba678-663e-4d39-b52e-b0910b550704",
      "display_name": "apple"
    },
    {
      "id": "http://localhost:8000/api/authors/34fdbd45-99b3-4c7b-a906-42e6a83e35c3",
      "display_name": "motorola"
    }
  ]
}
```

<br><br><br>


## /api/sync_remote_authors/

Begins the process of synchronizing author information from all remote nodes asynchronously (in the background). <br>
The server immediately responds with {"status": "ok"} while the synchronization task continues to run in a separate thread. <br>

This is a simple GET request — no request body is required.

### Endpoint: GET /api/sync_remote_authors

### Response
```json
{
    "status": "ok"
}
```



























































































<!-- // Post creation and feed retrieval

// ##### api/author/<author_id>/entries/ #####

// Retrieves a list of entries (posts) created by the given author.
// Requires authentication

// Endpoint:
// GET /api/authors/<author_uuid>>/entries/
// Authorization: Token <your-token>

// Successful Response: '200 OK'
// '''json
// [
//     {
//         "id": "6205f351-f399-415f-809c-42fd021a4f48",
//         "imageType": null,
//         "visibility": "PUBLIC",
//         "title": "Random Idea",
//         "content": "# Heading One\nSome content below.",
//         "contentType": "text/markdown",
//         "created_at": "2025-06-18T06:01:18.615836Z",
//         "updated_at": "2025-06-18T06:01:18.615854Z",
//         "description": "Experimenting...",
//         "is_deleted": false,
//         "author": "81128ca9-b713-4d14-9399-0449998722ac"
//     },
//     {
//         "id": "afc0838d-ac84-4dff-b174-ac544b4690a5",
//         "imageType": null,
//         "visibility": "FRIENDS",
//         "title": "Hello World",
//         "content": "Look at this _italic_ word.",
//         "contentType": "text/plain",
//         "created_at": "2025-06-18T06:01:18.523476Z",
//         "updated_at": "2025-06-18T06:01:18.523487Z",
//         "description": "Look at this",
//         "is_deleted": false,
//         "author": "81128ca9-b713-4d14-9399-0449998722ac"
//     },
//     ...
// ]

// Endpoint:
// POST /api/authors/<author_uuid>>/entries/
// Authorization: Token <your-token>
// Content-Type: application/json
// '''json
// {
//   "title": "New Post",
//   "content": "Hello world!",
//   "contentType": "text/markdown",
//   "visibility": "FRIENDS"
// }

// ### or you could set it to base64 to send image ###
// ### then you would have to add imageType ***

// Successful Response: '201 Created'
// '''json
// {
//     "id": "4eb4d529-b534-4378-ab12-8da319538503",
//     "imageType": null,
//     "visibility": "FRIENDS",
//     "title": "New Post",
//     "content": "Hello world!",
//     "contentType": "text/markdown",
//     "created_at": "2025-06-19T07:44:48.925864Z",
//     "updated_at": "2025-06-19T07:44:48.925875Z",
//     "description": "",
//     "is_deleted": false,
//     "author": "81128ca9-b713-4d14-9399-0449998722ac"
// }

// ### if contentType, visibility is not within ###
// CONTENT_TYPE_CHOICES = [
//         ("text/markdown", "Markdown"),
//         ("text/plain", "Plain text"),
//         ("application/base64", "Base64"),
//         ("image/png;base64", "PNG image"),
//         ("image/jpeg;base64", "JPEG image"),
//     ]

// VISIBILITY_CHOICES = [
//         ("PUBLIC", "Public"),
//         ("FRIENDS", "Friends only"),
//         ("UNLISTED", "Unlisted"),
//     ]

// ### Then you get 400 BAD REQUEST ###
// '''json
// {
//     "visibility": [
//         "\"FRIENDasdfS\" is not a valid choice."
//     ],
//     "contentType": [
//         "\"te214adsfxt/markdown\" is not a valid choice."
//     ]
// }





// ##### api/author/<author_id>/entries/<entry_id> #####

// Manages a single post (entry) belonging to a specific author.
// This endpoint allows reading, updating, or deleting the post. (GET, PUT, PATCH, DELETE)
// All requests require authentication. Only the owner of the post may modify or delete it.

// Endpoint:
// GET /api/authors/<author_id>/entries/<entry_id>/

// Successful Response: '200 OK'
// '''json
// {
//     "id": "6205f351-f399-415f-809c-42fd021a4f48",
//     "imageType": null,
//     "visibility": "PUBLIC",
//     "title": "Random Idea",
//     "content": "# Heading One\nSome content below.",
//     "contentType": "text/markdown",
//     "created_at": "2025-06-18T06:01:18.615836Z",
//     "updated_at": "2025-06-18T06:01:18.615854Z",
//     "description": "Experimenting...",
//     "is_deleted": false,
//     "author": "81128ca9-b713-4d14-9399-0449998722ac"
// }


// Endpoint:
// PATCH /api/authors/<author_id>/entries/<entry_id>/
// '''json
// {
//     "title": "new title"
// }

// Successful Response: '200 OK'
// '''json
// {
//     "id": "6205f351-f399-415f-809c-42fd021a4f48",
//     "imageType": null,
//     "visibility": "PUBLIC",
//     "title": "new title",
//     "content": "# Heading One\nSome content below.",
//     "contentType": "text/markdown",
//     "created_at": "2025-06-18T06:01:18.615836Z",
//     "updated_at": "2025-06-18T06:01:18.615854Z",
//     "description": "Experimenting...",
//     "is_deleted": false,
//     "author": "81128ca9-b713-4d14-9399-0449998722ac"
// }

// ### see that "title" has changed ###


// Endpoint:
// DELETE /api/authors/<author_id>/entries/<entry_id>/
// curl -X DELETE http://localhost:8000/api/authors/ddf2b3c8-1087-4505-a2f4-7bd37ba3220d/entries/5bfde182-db6a-4ac9-8dd7-81af8bf463e9/ \
//   -H "X-CSRFToken: f8Ys1DlvrCExQxbh9gxKMiEdxSsJPmLK" \
//   -H "Cookie: sessionid=8ejs7pfo296zdmj6xjjnc61c3owaqk7o; csrftoken=f8Ys1DlvrCExQxbh9gxKMiEdxSsJPmLK"

// ### this returns 204 if author_id, entry_id, csrf_token, cookies are all accurate ###


// Commenting and liking system

// ##### /api/authors/<author_uuid>/entries/<entry_uuid>/comment/ #####

// Create a new comment on the specified entry.
// Requires authentication. The comment will be linked to the authenticated author.

// Endpoint:
// POST /api/authors/<author_uuid>/entries/<entry_uuid>/comment/

// Request:
// '''json
// {
//   "content": "This is a comment"
// }

// Successful Resopnse: '201 CREATED'
// '''json
// {
//   "id": "<comment_uuid>",
//   "entry": "<entry_uuid>",
//   "author": "<author_uuid>",
//   "content": "This is a comment",
//   "created_at": "..."
// }

// Endpoint:
// GET /api/authors/<author_uuid>/entries/<entry_uuid>/comment/

// Retrieve a list of comments on the entry.
// Returns the most recent comments (optionally paginated).

// '200 OK'
// [
//   {
//     "id": "<comment_uuid>",
//     "author": "<author_uuid>",
//     "content": "Nice post!",
//     "created_at": "..."
//   },
//   ...
// ]

// ### PATCH FOR api/comment is not being used ###

// Delete a comment. Only the original comment author (or admin) can delete.

// Endpoint:
// DELETE /api/authors/<author_uuid>/entries/<entry_uuid>/comment/<comment_uuid>/

// Response: 204

// ##### /api/authors/<author_id>/entries/<entry_id>/like

// Endpoint:
// POST /api/authors/<author_id>/<entry_id>/like/
// Request:
// '''json
// {}

// Successful Response: '201 CREATED'
// '''json
// {
//   "id": "<like_uuid>",
//   "author": "<author_uuid>",
//   "entry": "<entry_uuid>",
//   "created_at": "..."
// }

// Endpoint:
// DELETE /api/authors/<author_id>/entries/<entry_id>/like/

// Unlike (remove like). Only the user who liked the entry can remove it.

// Response: 204


// ### If already liked, then it says that the entry has already been liked ###

// Endpoint:
// GET /api/authors/<author_id>/entries/<entry_id>/like/

// Retrieve a list of likes on the given entry.

// Successful Response: 200 OK
// '''json
// [
//   {
//     "id": "<like_uuid>",
//     "author": "<author_uuid>",
//     "entry": "<entry_uuid>",
//     "created_at": "..."
//   },
//   ...
// ]



// Follow/friend request workflow



 -->
