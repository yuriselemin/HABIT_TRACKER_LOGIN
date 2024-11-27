from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import timedelta, datetime
from .models import Habit, DailyProgress, Users
from .forms import HabitForm, DailyProgressForm
from matplotlib import pyplot as plt
from io import BytesIO
import base64
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .forms import LoginForm




def login_user(request):
    if request.method == 'POST':
        form = LoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('/home/')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})




# Функция для страницы приветствия
def welcome(request):
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'welcome.html')




# Функция регистрации нового пользователя
def register_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        if password != confirm_password:
            messages.error(request, "Пароли не совпадают!")
            return redirect('register')
        try:
            User.objects.get(username=username)
            messages.error(request, "Такой пользователь уже существует!")
            return redirect('register')
        except User.DoesNotExist:
            user = User.objects.create_user(username=username, password=password)
            users_profile = Users(user=user, first_name=username, last_name=last_name)
            users_profile.save()
            login(request, user)
            messages.success(request, "Вы успешно зарегистрированы!")
            return redirect('home')
    return render(request, 'register.html')




# Представление для добавления новой привычки
@login_required
def add_habit(request):
    if request.method == 'POST':
        form = HabitForm(request.POST)
        if form.is_valid():
            habit = form.save(commit=False)
            habit.user = request.user
            habit.start_date = datetime.now().date()
            habit.end_date = habit.start_date + timedelta(days=40)
            habit.save()
            messages.success(request, "Привычка была успешно создана!")
            return redirect('home')
    else:
        form = HabitForm()
    return render(request, 'add_habit.html', {'form': form})




# Функционал для фиксации ежедневного прогресса
@login_required
def daily_progress(request, habit_id):
    habit = Habit.objects.get(id=habit_id)
    today = datetime.now().date()  # Текущая дата

    # Проверяем, есть ли запись о прогрессе за сегодняшний день
    today_progress = habit.daily_progress.filter(date=today).exists()

    # Переносим функциональность сюда
    progress_data = habit.daily_progress.all().values_list('date', 'completed')
    dates = [p[0].strftime('%d-%m-%Y') for p in progress_data]
    completions = [bool(p[1]) for p in progress_data]
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(dates, completions, marker='o', linestyle='-', color='b')
    ax.set_xlabel('Дата')
    ax.set_ylabel('Статус выполнения')
    ax.grid(True)
    buf = BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    graph = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)

    if request.method == 'POST':
        form = DailyProgressForm(request.POST)

        if form.is_valid():
            progress = form.save(commit=False)
            progress.habit = habit
            progress.date = today

            # Проверяем состояние чекбокса
            if not progress.completed:
                messages.warning(request, "Не отмечено!")
                return redirect('home')

            # Проверяем, есть ли запись за этот день
            elif today_progress:
                messages.info(request, "Сегодня уже зафиксировано!")
                return redirect('home')

            progress.save()
            messages.success(request, "Прогресс был зафиксирован!")
            return redirect('home')
    else:
        form = DailyProgressForm()

    context = {'form': form, 'habit': habit, 'graph': graph}  # Передаем график в контекст
    return render(request, 'daily_progress.html', context)




# Главная страница с перечнем привычек пользователя
@login_required
def home(request):
    habits = Habit.objects.filter(user=request.user).order_by('-start_date')

    page = request.GET.get('page', 1)  # Получаем номер текущей страницы
    paginator = Paginator(habits, 5)  # Создаем объект пагинатора, показываем по 5 привычек на одной странице

    try:
        habits_page = paginator.page(page)
    except PageNotAnInteger:
        habits_page = paginator.page(1)
    except EmptyPage:
        habits_page = paginator.page(paginator.num_pages)

    return render(request, 'home.html', {'habits': habits_page})  # Передаем пагинацию в шаблон

def about_us(request):
    return render(request, 'about_us.html')

