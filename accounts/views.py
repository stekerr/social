from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from django.template.context_processors import csrf
from accounts.forms import UserRegistrationForm, UserLoginForm
from django.core.mail import EmailMessage
from django.conf import settings
import stripe
import datetime
from accounts.models import User
from django.http import HttpResponse
import arrow
import json
from django.views.decorators.csrf import csrf_exempt
# from views import paypal_return, paypal_cancel

stripe.api_key = settings.STRIPE_SECRET

'''**Initial register function**

def register(request, register_form=UserRegistrationForm):
    if request.method == 'POST':
        form = register_form(request.POST)
        if form.is_valid():
            form.save()
            user = auth.authenticate(email=request.POST.get('email'),
                                     password=request.POST.get('password1'))
            if user:
                messages.success(request, "Thank you, your payment was authorised. You have successfully registered!")
                email = EmailMessage('Confirmation', 'This is a confirmation email')
                email.send()
                return redirect(reverse('login'))
            else:
                messages.error(request, 'unable to log you in at this time!')
    else:
        form = register_form()
    args = {'form': form}
    args.update(csrf(request))
    return render(request, 'register.html', args)

    **Initial register function'''


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():

            try:
                customer = stripe.Customer.create(
                    email=form.cleaned_data['email'],
                    card=form.cleaned_data['stripe_id'],
                    plan='REG_MONTHLY',
                )

                # our initial code for a single payment**
                '''customer = stripe.Charge.create(
                    amount=499,
                    currency='USD',
                    description=form.cleaned_data['email'],
                    card=form.cleaned_data['stripe_id'],
                )'''
                # our initial code for a single payment

            except stripe.error.CardError, e:
                messages.error(request, "Your card was declined!")
            # initial code
            '''if customer.paid:
                form.save()

                user = auth.authenticate(email=request.POST.get('email'),
                                         password=request.POST.get('password1'))'''
            # initial code
            if customer:
                user = form.save()
                user.stripe_id = customer.id
                user.subscription_end = arrow.now().replace(weeks=+4).datetime
                user.save()

                user = auth.authenticate(email=request.POST.get('email'),
                                         password=request.POST.get('password1'))

                if user:
                    auth.login(request, user)
                    messages.success(request, "Thank you, your card was authorised. You have successfully registered!")
                    return redirect(reverse('profile'))

                else:
                    messages.error(request, "unable to log you in at this time!")
            else:
                messages.error(request, "We were unable to take a payment with that card!")

    else:
        today = datetime.date.today()
        form = UserRegistrationForm(initial={'expiry_month': today.month,
                                             'expiry_year': today.year})

    args = {'form': form, 'publishable': settings.STRIPE_PUBLISHABLE}
    args.update(csrf(request))

    return render(request, 'register.html', args)


def login(request, success_url=None):
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = auth.authenticate(email=request.POST.get('email'),
                                     password=request.POST.get('password'))

            if user is not None:
                auth.login(request, user)
                messages.error(request, "You have successfully logged in")
                return redirect(reverse('profile'))
            else:
                form.add_error(None, "Your email or password was not recognised")
        else:
            return render(request, 'contact.html', {'form': form})
    else:
        form = UserLoginForm()

    args = {'form': form}
    args.update(csrf(request))
    return render(request, 'login.html', args)


@login_required(login_url='/accounts/login/')
def cancel_subscription(request):  # new subscription code
    try:
        customer = stripe.Customer.retrieve(request.user.stripe_id)

        customer.cancel_subscription(at_period_end=True)
    except Exception, e:
        messages.error(request, e)

    return redirect('profile')


def profile(request):
    return render(request, 'profile.html')


def logout(request):
    auth.logout(request)
    messages.success(request, 'You have successfully logged out')
    return render(request, 'index.html')


@csrf_exempt
def paypal_return(request):
    args = {'post': request.POST, 'get': request.GET}
    return render(request, 'paypal_return.html', args)


def paypal_cancel(request):
    args = {'post': request.POST, 'get': request.GET}
    return render(request, 'paypal_cancel.html', args)


def subscriptions_webhook(request):
    event_json = json.loads(request.body)

    try:
        event = stripe.Event.retrieve(event_json["id"])

        user = User.objects.get(stripe_id=event_json["customer"])

        if user and event_json['type'] == "invoice.payment_succeeded":
            user.subscription_end = arrow.now().replace(weeks=+4).datetime
            user.save()

    except stripe.InvalidRequestError, e:
        return HttpResponse(status=404)

    return HttpResponse(status=200)
