from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
import requests
from myapp.models import Course
from myapp.models import Session
from myapp.models import Course, AppUser, Booking
from django.db.models import Q
from myapp.forms import SessionForm
from django.contrib import *
from django.views import generic
from django.shortcuts import get_object_or_404
from myapp.forms import BookingForm
from django.urls import reverse
from datetime import datetime, date, timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
import calendar
from .utils import Calendar
from django.utils.safestring import mark_safe

def fetch_courses():
    # courses = []
    url = 'https://sisuva.admin.virginia.edu/psc/ihprd/UVSS/SA/s/WEBLIB_HCX_CM.H_CLASS_SEARCH.FieldFormula.IScript_ClassSearch?institution=UVA01&term=1232&acad_career=UGRD'

    for x in range(40, 44):
        data = requests.get(url + '&page=' + str(x))
        for c in data.json():
            if Course.objects.filter(sub_and_cat__icontains=c['subject'] + " " + c['catalog_nbr']):
                pass
            else:
                course = Course(
                    subject=c['subject'],
                    catalog_number=c['catalog_nbr'],
                    sub_and_cat=c['subject'] + " " + c['catalog_nbr'],
                    class_section=c['class_section'],
                    class_number=c['class_nbr'],
                    class_title=c['descr'],
                    instructor=c['instructors'],
                )
                course.save()  # save the course instance to the database
            # courses.append(course)

    # print(f"Fetched {len(courses)} courses")
    return


@login_required
def course_list(request):
    subject_query = request.GET.get('sub')
    catalog_query = request.GET.get('cat')
    title_query = request.GET.get('course_title')
    courses = Course.objects.all()
    logged_in_user = request.user
    email = logged_in_user.email
    try:
        current_user = AppUser.objects.get(pk=email)
    except AppUser.DoesNotExist:
        return redirect('login.html')
    if subject_query:
        subject_list = courses.filter(Q(subject__icontains=subject_query))
        courses = subject_list
    if catalog_query:
        catalog_list = courses.filter(Q(catalog_number__icontains=catalog_query))
        courses = catalog_list
    if title_query:
        title_list = courses.filter(Q(class_title__icontains=title_query))
        courses = title_list
    if (not subject_query) & (not catalog_query) & (not title_query):
        courses = Course.objects.all()
    return render(request, 'course_list.html', {'courses': courses, 'cur_User': current_user})


@login_required
def view_sessions(request, pk):
    course = get_object_or_404(Course, pk=pk)
    sessions = Session.objects.filter(course=course)
    logged_in_user = request.user
    if logged_in_user.is_anonymous:
        return redirect('/login/')
    try:
        email = logged_in_user.email
        current_user = AppUser.objects.get(pk=email)
        return render(request, 'course_session_view.html',
                      {'sessions': sessions, 'course': course, 'cur_User': current_user})
    except AppUser.DoesNotExist:
        return redirect("login.html")
    return render(request, 'course_session_view.html', {'sessions': sessions, 'course': course})


def login(request):
    return render(request, 'login.html')


def index(request):
    return render(request, 'template.html', {})


@login_required
def home(request):
    logged_in_user = request.user
    email = logged_in_user.email
    try:
        current_user = AppUser.objects.get(pk=email)
    except AppUser.DoesNotExist:
        if request.method == 'POST':
            role = request.POST.get('role')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            if role == 'tutor':
                new_user = AppUser(email=email, first_name=first_name,
                                   last_name=last_name, user_role=AppUser.TUTOR)
                new_user.save()
                return redirect('tutor-home')
            elif role == 'student':
                new_user = AppUser(email=email, first_name=first_name,
                                   last_name=last_name, user_role=AppUser.STUDENT)
                new_user.save()
                return redirect('student-home')
        else:
            return render(request, 'home.html')

    if current_user is not None:
        if current_user.user_role == AppUser.STUDENT:
            return redirect('student-home')
        elif current_user.user_role == AppUser.TUTOR:
            return redirect('tutor-home')


@login_required
def student_home(request):
    logged_in_user = request.user
    email = logged_in_user.email
    try:
        current_user = AppUser.objects.get(pk=email)
        if (current_user.user_role == AppUser.TUTOR):
            return redirect('tutor_home.html')
    except AppUser.DoesNotExist:
        return redirect('login.html')
    try:
        bookings = Booking.objects.filter(user=logged_in_user)
    except Booking.DoesNotExist:
        bookings = None
    return render(request, 'student_home.html', {'cur_User': current_user, 'bookings': bookings})


@login_required
def tutor_home(request):
    logged_in_user = request.user
    email = logged_in_user.email
    try:
        current_user = AppUser.objects.get(pk=email)
        if (current_user.user_role == AppUser.STUDENT):
            return redirect('student_home.html')
    except AppUser.DoesNotExist:
        return redirect('login.html')
    return render(request, 'tutor_home.html', {'cur_User': current_user})


@login_required
def current_sessions(request):
    logged_in_user = request.user
    email = logged_in_user.email
    if (request.method == 'POST'):
        cur_bookingid = request.POST.get('cur_booking')
        cur_booking = Booking.objects.get(pk=cur_bookingid)
        appointment_selection = request.POST.get('decision')
        if (appointment_selection == "accept"):
            cur_booking.booking_status = Booking.ACCEPTED
        elif (appointment_selection == "reject"):
            cur_booking.booking_status = Booking.DECLINED
        cur_booking.save()
    try:
        current_user = AppUser.objects.get(pk=email)
    except AppUser.DoesNotExist:
        # Prob a better way to ensure safety; let's implement later
        return render(request, 'current_sessions.html')
    # Get all bookings
    # Option to decline or accept if pending
    try:
        sessions = Session.objects.filter(tutor=logged_in_user)
    except Session.DoesNotExist:
        sessions = None
    bookings = []
    for session in sessions:
        # Will need to make a check so that you can only have one booking per session
        try:
            booking = Booking.objects.get(session=session)
        except Booking.DoesNotExist:
            booking = None
        if (booking != None):
            bookings.append(booking)

    return render(request, 'current_sessions.html', {'cur_User': current_user, 'bookings': bookings})


@login_required
def current_appointments(request):
    logged_in_user = request.user
    email = logged_in_user.email
    try:
        current_user = AppUser.objects.get(pk=email)
    except AppUser.DoesNotExist:
        # Prob a better way to ensure safety; let's implement later
        return render(request, 'current_appointments.html')
    # Get all bookings
    try:
        bookings = Booking.objects.filter(user=logged_in_user)
    except Booking.DoesNotExist:
        bookings = None

    return render(request, 'current_appointments.html', {'cur_User': current_user, 'bookings': bookings})


@login_required
def post_session(request):
    if request.method == 'POST':
        form = SessionForm(request.POST)
        if form.is_valid():
            course = form.cleaned_data['course']
            session = form.save(commit=False)
            session.tutor = request.user
            session.course = course
            session.save()
            messages.success(request, 'Session posted successfully.', fail_silently=True)
            return redirect('tutor-home')
    else:
        form = SessionForm()

    return render(request, 'post_session.html', {'form': form})


@login_required
def book_session(request, session_id):
    session = get_object_or_404(Session, id=session_id)
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.session = session
            booking.user = request.user._wrapped if hasattr(
                request.user, '_wrapped') else request.user
            booking.save()
            messages.success(request, 'Session booked successfully!')

            # Render the booking confirmation template
            return render(request, 'booking_confirmation.html', {'booking': booking})
    else:
        form = BookingForm()

    return render(request, 'book_session.html', {'form': form, 'session': session})


@login_required
def booking_confirmation(request, course_id):
    if request.method == 'POST':
        return redirect('course_list')
    return render(request, 'booking_confirmation.html', {'course_id': course_id})


class CalendarView(LoginRequiredMixin, generic.ListView):
    model = Booking
    template_name = 'calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # use today's month for the calendar
        d = get_date(self.request.GET.get('month', None))

        # Instantiate our calendar class with today's year and date, and the current user
        cal = Calendar(d.year, d.month, self.request.user)

        # Call the formatmonth method, which returns our calendar as a table
        html_cal = cal.formatmonth(withyear=True)
        context['calendar'] = mark_safe(html_cal)
        context['prev_month'] = prev_month(d)
        context['next_month'] = next_month(d)
        return context


def get_date(req_day):
    if req_day:
        year, month = (int(x) for x in req_day.split('-'))
        return date(year, month, day=1)
    return datetime.today()


def prev_month(d):
    first = d.replace(day=1)
    prev_month = first - timedelta(days=1)
    month = 'month=' + str(prev_month.year) + '-' + str(prev_month.month)
    return month


def next_month(d):
    days_in_month = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=days_in_month)
    next_month = last + timedelta(days=1)
    month = 'month=' + str(next_month.year) + '-' + str(next_month.month)
    return month
