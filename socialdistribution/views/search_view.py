from django.shortcuts import redirect, get_object_or_404
from django.views import View
from socialdistribution.models import Author, RemoteNode
from django.http import JsonResponse
from django.views.decorators.http import require_GET
import threading
from socialdistribution.utils import sync_remote_authors

class AuthorSearchView(View):
    def get(self, request):
        query = request.GET.get("q", "").strip()
        author = get_object_or_404(Author, display_name__iexact=query)
        return redirect("profile_page", pk=author.id)
    
def author_autocomplete(request):
    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"results": []})
    
    authors = Author.objects.filter(display_name__icontains=q)[:5]
    data = [{"id": str(author.id), "display_name": author.display_name} for author in authors]
    return JsonResponse({"results": data})

@require_GET
def sync_remote_authors_view(request):
    def do_sync():
        for node in RemoteNode.objects.all():
            sync_remote_authors(node)

    threading.Thread(target=do_sync, daemon=True).start()
    return JsonResponse({"status": "ok"})
