from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.db import IntegrityError, models
from django.http import HttpResponse

from .models import Competitor, ResortCompetitorAssociation, ScrapingLink, ScrapedData
from .forms import CompetitorForm, ResortCompetitorAssociationForm, ScrapingLinkForm, CompetitorScrapingTaskForm
from resort.models import Resort
from accounts.models import User
from reviews.models import Review

class SuperuserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_superuser

class CompetitorListView(LoginRequiredMixin, SuperuserRequiredMixin, ListView):
    model = Competitor
    template_name = 'competitors/competitor_list.html'
    context_object_name = 'competitors'
    paginate_by = 20
    def get_queryset(self):
        return Competitor.objects.select_related('company')

class CompetitorCreateView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = Competitor
    form_class = CompetitorForm
    template_name = 'competitors/competitor_form.html'
    success_url = reverse_lazy('competitors:competitor-list')
    def form_valid(self, form):
        messages.success(self.request, "Competitor creato con successo.")
        return super().form_valid(form)

class CompetitorUpdateView(LoginRequiredMixin, SuperuserRequiredMixin, UpdateView):
    model = Competitor
    form_class = CompetitorForm
    template_name = 'competitors/competitor_form.html'
    success_url = reverse_lazy('competitors:competitor-list')
    def get_queryset(self):
        return Competitor.objects.all()
    def form_valid(self, form):
        messages.success(self.request, "Competitor aggiornato con successo.")
        return super().form_valid(form)

class CompetitorDeleteView(LoginRequiredMixin, SuperuserRequiredMixin, DeleteView):
    model = Competitor
    template_name = 'competitors/competitor_confirm_delete.html'
    success_url = reverse_lazy('competitors:competitor-list')
    def get_queryset(self):
        return Competitor.objects.all()
    def form_valid(self, form):
        messages.success(self.request, f"Competitor '{self.object.name}' eliminato con successo.")
        return super().form_valid(form)

@login_required
def manage_competitor_links_modal(request, pk):
    if not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=403)
    competitor = get_object_or_404(Competitor, pk=pk)
    if request.method == 'POST':
        form = ScrapingLinkForm(request.POST)
        if form.is_valid():
            new_link = form.save(commit=False)
            new_link.competitor = competitor
            platform_options = {}
            source = form.cleaned_data.get('source')
            if source.name == 'Booking.com' and form.cleaned_data.get('max_reviews_booking'):
                platform_options['maxReviewsPerHotel'] = form.cleaned_data.get('max_reviews_booking')
            elif source.name == 'Google Maps' and form.cleaned_data.get('max_reviews_google'):
                platform_options['maxReviews'] = form.cleaned_data.get('max_reviews_google')
            elif source.name == 'Tripadvisor' and form.cleaned_data.get('max_reviews_tripadvisor'):
                platform_options['maxReviews'] = form.cleaned_data.get('max_reviews_tripadvisor')
            new_link.platform_options = platform_options
            try:
                new_link.save()
                messages.success(request, "Link aggiunto.")
            except IntegrityError:
                messages.error(request, "Link duplicato.")
        form = ScrapingLinkForm()
    else:
        form = ScrapingLinkForm()
    scraping_links = competitor.scraping_links.all().select_related('source')
    context = {'competitor': competitor, 'scraping_links': scraping_links, 'form': form}
    return render(request, 'competitors/partials/modal_content.html', context)

@login_required
def delete_scraping_link(request, pk):
    if not request.user.is_superuser:
        return HttpResponse("Unauthorized", status=403)
    scraping_link = get_object_or_404(ScrapingLink, pk=pk)
    competitor = scraping_link.competitor
    if request.method == 'POST':
        scraping_link.delete()
        messages.success(request, "Link eliminato.")
    form = ScrapingLinkForm()
    scraping_links = competitor.scraping_links.all().select_related('source')
    context = {'competitor': competitor, 'scraping_links': scraping_links, 'form': form}
    return render(request, 'competitors/partials/modal_content.html', context)

class ManageCompetitorAssociationsView(LoginRequiredMixin, SuperuserRequiredMixin, CreateView):
    model = ResortCompetitorAssociation
    form_class = ResortCompetitorAssociationForm
    template_name = 'competitors/manage_associations.html'
    def get_resort(self):
        return get_object_or_404(Resort, pk=self.kwargs['resort_pk'])
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resort = self.get_resort()
        context['resort'] = resort
        context['associated_competitors'] = ResortCompetitorAssociation.objects.filter(resort=resort).select_related('competitor')
        context['available_competitors'] = Competitor.objects.exclude(id__in=context['associated_competitors'].values_list('competitor_id', flat=True))
        return context
    def form_valid(self, form):
        resort = self.get_resort()
        competitor = form.cleaned_data['competitor']
        ResortCompetitorAssociation.objects.create(resort=resort, competitor=competitor)
        messages.success(self.request, f"Competitor '{competitor.name}' associato a '{resort.name}'.")
        return redirect(self.get_success_url())
    def get_success_url(self):
        return reverse('competitors:manage-associations', kwargs={'resort_pk': self.kwargs['resort_pk']})

@login_required
def remove_competitor_association(request, pk):
    if not request.user.is_superuser:
        messages.error(request, "Azione non permessa.")
        return redirect('home')
    association = get_object_or_404(ResortCompetitorAssociation, pk=pk)
    resort_pk = association.resort.pk
    if request.method == 'POST':
        association.delete()
        messages.success(request, "Associazione rimossa con successo.")
    return redirect('competitors:manage-associations', resort_pk=resort_pk)

from .services import trigger_competitor_scraping

@login_required
def competitor_scraping_panel_view(request):
    if not request.user.is_superuser:
        messages.error(request, "Non hai il permesso di accedere a questa sezione.")
        return redirect('home')
    if request.method == 'POST':
        form = CompetitorScrapingTaskForm(request.POST)
        if form.is_valid():
            competitors_to_scrape = form.cleaned_data['competitors']
            link_ids = list(ScrapingLink.objects.filter(competitor__in=competitors_to_scrape, is_active=True).values_list('id', flat=True))
            if not link_ids:
                messages.warning(request, "Nessun link di scraping attivo trovato per i competitor selezionati.")
                return redirect('competitors:scraping-panel')
            summary = trigger_competitor_scraping(scraping_link_ids=link_ids)
            messages.success(request, f"Scraping avviato per {len(link_ids)} link. Controllare i log per i dettagli.")
            return redirect('competitors:scraping-panel')
    else:
        form = CompetitorScrapingTaskForm()
    context = {'form': form, 'page_title': 'Pannello di Scraping Manuale per Competitor'}
    return render(request, 'competitors/competitor_scraping_panel.html', context)
