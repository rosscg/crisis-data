from django import forms
from .models import Event, GeoPoint


class EventForm(forms.ModelForm):

    class Meta:
        model = Event
        fields = ('name', 'time_start', 'time_end')


class GPSForm(forms.ModelForm):

    class Meta:
        model = GeoPoint
        fields = ('latitude', 'longitude')
