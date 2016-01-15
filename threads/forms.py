from django import forms
from .models import Thread, Posts


class ThreadForm(forms.ModelForm):
    class Meta:
        model = Thread
        fields = ['name']


class PostForm(forms.ModelForm):
    class Meta:
        model = Posts
        fields = ['comment']
