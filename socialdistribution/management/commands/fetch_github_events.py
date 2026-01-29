# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-07-09
import requests
from urllib.parse import urlparse
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from socialdistribution.models import Author, Entry



class Command(BaseCommand):
    help = """
    Fetch latest public GitHub events for all Authors with a github_link,
    and create corresponding Entry objects.

    - title = event type (e.g. PushEvent)
    - content = "<repo_name>: <message>" for each commit (PushEvent) or repo name fallback
    """

    def handle(self, *args, **options):
        # Only process authors who have set a GitHub profile URL
        authors = Author.objects.filter(
            github_link__isnull=False
        ).exclude(github_link__exact="")

        # Prepare headers (optional token for higher rate limit)
        headers = {"Accept": "application/vnd.github+json"}
        token = getattr(settings, 'GITHUB_TOKEN', None)
        if token:
            headers['Authorization'] = f'token {token}'

        for author in authors:
            # Extract GitHub username from URL
            parsed = urlparse(author.github_link)
            username = parsed.path.strip('/')
            if not username:
                self.stdout.write(self.style.WARNING(
                    f"Invalid github_link for author {author.id}: {author.github_link}"
                ))
                continue

            api_url = f"https://api.github.com/users/{username}/events/public"
            try:
                resp = requests.get(api_url, headers=headers, timeout=10)
                resp.raise_for_status()
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Failed to fetch events for {username}: {e}"
                ))
                continue

            events = resp.json()
            for ev in events:
                ev_type   = ev.get('type', '')
                repo_name = ev.get('repo', {}).get('name', '')
                # Build content: for PushEvent, list commit messages
                lines = []
                if ev_type == 'PushEvent':
                    commits = ev.get('payload', {}).get('commits', [])
                    for c in commits:
                        msg = c.get('message', '').strip()
                        if msg:
                            lines.append(f"{repo_name}: {msg}")
                # Fallback: just show repo name
                if not lines:
                    lines = [repo_name]

                content = '\n'.join(lines)

                created_at_str = ev.get('created_at')
                dt = None
                if created_at_str:
                    dt = parse_datetime(created_at_str)  # 变成 naive datetime
                    if dt and timezone.is_naive(dt):
                        dt = timezone.make_aware(dt, timezone.utc)
                if not dt:
                    dt = timezone.now()

                event_id = ev.get('id')
                # Build the full URL for the Entry.id primary key
                full_id = (
                    f"{settings.BASE_URL}/api/authors/{author.id}/entries/{event_id}"
                )

                # Create entry if not exists
                entry, created = Entry.objects.get_or_create(
                    id=full_id,
                    defaults={
                        'author':      author,
                        'visibility':  'PUBLIC',
                        'title':       f"[GitHub] {ev_type}",
                        'content':     content,
                        'contentType': 'text/plain',
                        'description': ev_type,
                        'created_at':  dt,
                        'updated_at':  dt,
                    }
                )
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Created Entry for {ev_type} in {repo_name} (event {event_id})"
                        )
                    )
                else:
                    self.stdout.write(
                        f"Entry already exists for event {event_id}"  
                    )

        self.stdout.write(self.style.SUCCESS("GitHub fetch complete."))