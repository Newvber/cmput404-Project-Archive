# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-07-09
from urllib.parse import urlparse
import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from socialdistribution.models import Author, Entry
from socialdistribution.utils import broadcast_entry_to_remotes
from socialdistribution.serializers.entrydetailserializer import EntryDetailSerializer


class GitHubUpdateAPIView(APIView):
    """
    Post to this endpoint to pull public GitHub events for an author,
    creating new Entry objects only for events that don't already exist.
    """

    def post(self, request, author_id):
        author = get_object_or_404(Author, id=author_id)
        author_uuid = author.id.rstrip('/').split('/')[-1]

        link = author.github_link or ""
        if not link:
            return Response(
                {"detail": "No github link detected"},
                status=status.HTTP_400_BAD_REQUEST
            )

        parsed = urlparse(link)
        username = parsed.path.strip('/')
        if not username:
            return Response(
                {"detail": "Wrong github link. Try a new github link"},
                status=status.HTTP_400_BAD_REQUEST
            )

        api_url = f"https://api.github.com/users/{username}/events/public"
        headers = {"Accept": "application/vnd.github+json"}
        token = getattr(settings, "GITHUB_TOKEN", None)
        if token:
            headers["Authorization"] = f"token {token}"

        try:
            resp = requests.get(api_url, headers=headers, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            return Response(
                {"detail": f"Failed to fetch from GitHub: {e}"},
                status=status.HTTP_502_BAD_GATEWAY
            )

        events = resp.json()

        created_count = 0
        for ev in events:
            event_id = ev.get("id")
            if not event_id:
                continue

            full_id = f"{author.host}authors/{author_uuid}/entries/{event_id}"
            if Entry.objects.filter(id=full_id).exists():
                continue

            ev_type   = ev.get("type", "")
            repo_name = ev.get("repo", {}).get("name", "")

            lines = []
            if ev_type == "PushEvent":
                for c in ev.get("payload", {}).get("commits", []):
                    msg = c.get("message", "").strip()
                    if msg:
                        lines.append(f"{repo_name}: {msg}")
            if not lines:
                lines = [repo_name]
            content = "\n".join(lines)

            dt = None
            created_at = ev.get("created_at")
            if created_at:
                dt = parse_datetime(created_at)
                if dt and timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone.utc)
            if not dt:
                dt = timezone.now()

            entry = Entry.objects.create(
                id=full_id,
                author=author,
                visibility="PUBLIC",
                title=f"[GitHub] {ev_type}",
                content=content,
                contentType="text/plain",
                description=ev_type,
                created_at=dt,
                updated_at=dt,
            )
            data = EntryDetailSerializer(entry).data
            broadcast_entry_to_remotes(data)
            created_count += 1

        if created_count == 0:
            return Response(
                {"detail": "No entry needed to update"},
                status=status.HTTP_200_OK
            )
        return Response(
            {"detail": f"{created_count} new entr{'y' if created_count==1 else 'ies'} created"},
            status=status.HTTP_201_CREATED
        )
