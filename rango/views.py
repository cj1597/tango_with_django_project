from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.forms.widgets import MediaOrderConflictWarning
from django.http import HttpResponse, response
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.utils.decorators import method_decorator
from rango.bing_search import run_query
from rango.forms import CategoryForm, PageForm, UserForm, UserProfileForm
from rango.models import Category, Page, UserProfile


class IndexView(View):
    def get(self, request):
        """
        This method displays the Home Page of the website - 
        showing the Top 5 Most Liked Categories and Top 5 
        Most Viewed Pages both in descending order.
        """
        visitor_cookie_handler = CookieHandlerView()
        category_list = Category.objects.order_by('-likes')[:5]
        most_viewed_pages_list = Page.objects.order_by('-views')[:5]
        
        context_dict = {}
        context_dict['boldmessage'] ='Crunchy, creamy, cookie, candy, cupcake!'
        context_dict['categories'] = category_list
        context_dict['most_viewed_pages'] = most_viewed_pages_list

        visitor_cookie_handler.get(request)
        response = render(request, 'rango/index.html', context=context_dict)
        return response
    

class AboutView(View):
    def get(self, request):
        """
        This method shows the About Page and returns the 
        number of the page's visits.
        """
        context_dict = {}
        context_dict['visits'] = request.session['visits']
        context_dict['name'] = 'Clarence'
        return render(request, 'rango/about.html', context_dict)


class ShowCategoryView(View):
    context_dict = {}

    def populate_context_dict(self, category_name_slug):
        """
        This a helper method 
        """
        try:
            category = Category.objects.get(slug=category_name_slug)
            pages = Page.objects.filter(category=category).order_by('-views')
            self.context_dict['pages'] =  pages
            self.context_dict['category'] = category

        except Category.DoesNotExist:   
            self.context_dict['category'] = None
            self.context_dict['pages'] = None

    def get(self, request, category_name_slug):
        self.populate_context_dict(category_name_slug)
        return render(request, 'rango/category.html', self.context_dict)       

    def post(self, request, category_name_slug):
        self.populate_context_dict(category_name_slug)
        query = request.POST['query'].strip()
        if query:
            result_list = run_query(query)
            self.context_dict['result_list'] = result_list
            self.context_dict['retain_query'] = query

        return render(request, 'rango/category.html', self.context_dict)


class AddCategoryView(View):
    index = IndexView()
    @method_decorator(login_required)
    def get(self, request):
        form = CategoryForm()
        return render(request, 'rango/add_category.html', {'form': form})

    @method_decorator(login_required)
    def post(self, request):
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save(commit=True)
            return self.index.get(request)
        else:
            print(form.errors)
        return render(request, 'rango/add_category.html', {'form': form})


class AddPageView(View):

    category = ''

    def get_category(self, category_name_slug):
        try:
            self.category = Category.objects.get(slug=category_name_slug)
        except Category.DoesNotExist:
            self.category = None

    def get(self, request, category_name_slug):
        self.get_category(category_name_slug)
        form = PageForm()
        context_dict = {'form': form, 'category': self.category}
        return render(request, 'rango/add_page.html', context_dict)
    
    def post(self, request, category_name_slug):
        self.get_category(category_name_slug)
        form = PageForm(request.POST)
        if form.is_valid():
            if self.category:
                page = form.save(commit=False)
                page.category = self.category
                page.views = 0
                page.save()
                
                return redirect(reverse('rango:show_category', 
                    kwargs={'category_name_slug': category_name_slug}))
        else:
            print(form.errors)
    
        context_dict = {'form': form, 'category': self.category}
        return render(request, 'rango/add_page.html', context_dict)


class RestrictedView(View):
    @method_decorator(login_required)
    def get(self, request):
        return render(request, 'rango/restricted.html')


class CookieHandlerView(View):

    def get_server_side_cookie(self, request, cookie, default_val=None):
        val = request.session.get(cookie)
        if not val:
            val = default_val
        return val

    def get(self, request):
        visits = int(self.get_server_side_cookie(request, 'visits', '1'))
        last_visit_cookie = self.get_server_side_cookie(request, 'last_visit', str(datetime.now()))
        last_visit_time = datetime.strptime(last_visit_cookie[:-7], '%Y-%m-%d %H:%M:%S')

        if (datetime.now() - last_visit_time).seconds > 0:
            visits += 1
            request.session['last_visit'] = str(datetime.now())
        else:
            request.session['last_visit'] = last_visit_cookie
        request.session['visits'] = visits


class GoToUrlView(View):
    def get(self, request):
        if request.method == 'GET':
            page_id = request.GET.get('page_id')
            try:
                selected_page = Page.objects.get(id=page_id)
            except Page.DoesNotExist:
                return redirect(reverse('rango:index'))

            selected_page.views += 1
            selected_page.save()
            selected_page.last_visit = datetime.now()
            selected_page.save()

            return redirect(selected_page.url)
        return redirect (reverse('rango:index'))


class RegisterProfileView(View):
    @method_decorator(login_required)
    def get(self, request):
        form = UserProfileForm()
        return render(request, 'rango/profile_registration.html', {'form': form})

    @method_decorator(login_required)
    def post(self, request):
        form = UserProfileForm(request.POST, request.FILES)

        if form.is_valid():
            user_profile = form.save(commit=False)
            user_profile.user = request.user
            user_profile.save()

            return redirect('rango:index')
        else:
            print(form.errors)
        return render(request, 'rango/profile_registration.html', {'form': form})

    
class ProfileView(View):
    def get_user_details(self, username):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None
        userprofile = UserProfile.objects.get_or_create(user=user)[0]
        form = UserProfileForm({'website': userprofile.website,
                                'picture': userprofile.picture})
        return (user, userprofile, form)

    @method_decorator(login_required)
    def get(self, request, username):
        try:
            (user, userprofile, form) = self.get_user_details(username)
        except TypeError:
            return redirect('rango:index')
        context_dict = {'userprofile': userprofile,
                        'selecteduser': user,
                        'form': form}
        return render(request, 'rango/profile.html', context_dict)

    @method_decorator(login_required)
    def post(self, request, username):
        try:
            (user, userprofile, form) = self.get_user_details(username)
        except TypeError:
            return redirect('rango:index')
        form = UserProfileForm(request.POST, request.FILES, instance=userprofile)
        if form.is_valid():
            form.save(commit=True)
            return redirect('rango:profile', user.username)
        else:
            print(form.errors)
        context_dict = {'userprofile': userprofile,
                        'selecteduser': user,
                        'form': form}
        return render(request, 'rango/profile.html', context_dict)


class ListProfilesView(View):
    @method_decorator(login_required)
    def get(self, request):
        context_dict = {}
        profile = UserProfile.objects.all()
        context_dict['userprofile_list'] = profile
        context_dict['pictures'] = profile
        return render(request, 'rango/list_profiles.html', context_dict)

        
class LikeCategoryView(View):
    @method_decorator(login_required)
    def get(self, request):
        category_id = request.GET.get('category_id')
        try:
            category = Category.objects.get(id=int(category_id))
        except Category.DoesNotExist:
            return HttpResponse(-1)
        except ValueError:
            return HttpResponse(-1)
        category.likes = category.likes + 1
        category.save()
        return HttpResponse(category.likes)


class SuggestionView(View):

    def get_category_list(self, max_results=0, starts_with=''):
        category_list =[]

        if starts_with:
            category_list = Category.objects.filter(name__istartswith=starts_with)
        
        if max_results > 0:
            if len(category_list) > max_results:
                category_list = category_list[:max_results]

        return category_list

    def get(self, request):
        suggestion = request.GET['suggestion']
        category_list = self.get_category_list(max_results=8, starts_with=suggestion)

        if len(category_list) == 0:
            category_list = Category.objects.order_by('-likes')
        return render(request, 'rango/categories.html', {'categories': category_list})


class SearchAddPageView(View):
    @method_decorator(login_required)
    def get(self, request):
        category_id = request.GET['category_id']
        title = request.GET['title']
        url = request.GET['url']
        try:
            category = Category.objects.get(id=int(category_id))
        except Category.DoesNotExist:
            return HttpResponse('Error - category not found.')
        except ValueError:
            return HttpResponse('Error - bad category ID.')

        p = Page.objects.get_or_create(category=category, title=title, url=url)
        pages = Page.objects.filter(category=category).order_by('-views')
        return render(request, 'rango/page_listing.html', {'pages': pages})



        





    







