from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.contrib import messages


from .forms import PetitionCreateForm
from .models import Petition, PetitionVote

def petition_list(request):
    petitions = Petition.objects.all().order_by('-created_at')

    if request.user.is_authenticated:
        voted_ids = set(
            PetitionVote.objects.filter(user=request.user)
            .values_list('petition_id', flat=True)
        )
    else:
        voted_ids = set()

    context = {
        'petitions': petitions,
        'voted_ids': voted_ids,
    }
    return render(request, 'petitions/list.html', context)

def petition_detail(request, pk):
    petition = get_object_or_404(Petition.objects.select_related('posted_by').prefetch_related('votes'), pk=pk)
    user_has_voted = False
    if request.user.is_authenticated:
        user_has_voted = petition.votes.filter(user=request.user).exists()
    context = {
        'petition': petition,
        'user_has_voted': user_has_voted,
        'template_data': {'title': petition.title}
    }
    return render(request, 'petitions/detail.html', context)

@login_required
def petition_create(request):
    if request.method == 'POST':
        form = PetitionCreateForm(request.POST, request.FILES)
        if form.is_valid():
            petition = form.save(commit=False)
            petition.posted_by = request.user
            petition.save()
            return redirect(petition.get_absolute_url())
    else:
        form = PetitionCreateForm()
    return render(request, 'petitions/create.html', {'form': form})

@login_required
@require_POST
def petition_vote(request, pk):
    petition = get_object_or_404(Petition, pk=pk)

    already_voted = PetitionVote.objects.filter(
        petition=petition, user=request.user
    ).exists()

    if already_voted:
        messages.warning(request, "You have already voted for this petition.")
    else:
        PetitionVote.objects.create(petition=petition, user=request.user)
        messages.success(request, "Your vote has been added!")

    return redirect("petitions:index")