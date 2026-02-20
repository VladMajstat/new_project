from django import forms


class DocumentUploadForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        file = self.cleaned_data.get('file')
        name = (file.name or '').lower()
        if not name.endswith('.pdf'):
            raise forms.ValidationError('Only PDF files are allowed')
        
        max_size = 1024 * 1024 * 10
        if file.size > max_size:
            raise forms.ValidationError('File size must be under 10MB')
        return file


class ReviewForm(forms.Form):
    """Form for reviewing and editing parsed prescription data."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            for field_name, field in self.fields.items():
                if field_name in self.errors:
                    classes = field.widget.attrs.get('class', '').split()
                    if 'is-invalid' not in classes:
                        classes.append('is-invalid')
                    field.widget.attrs['class'] = ' '.join(filter(None, classes))

    # Block 1: Insurance
    block1_insurance__krankenkasse = forms.CharField(
        required=False, max_length=255, label='Krankenkasse',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Krankenkasse must be at most 255 characters.'}
    )
    block1_insurance__status = forms.CharField(
        required=False, max_length=50, label='Status',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Status must be at most 50 characters.'}
    )
    
    # Block 2: Patient
    block2_patient__patiant_surname = forms.CharField(
        required=True, max_length=255, label='Surname (Nachname)',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={
            'required': 'Surname is required.',
            'max_length': 'Surname must be at most 255 characters.'
        }
    )
    block2_patient__patiant_name = forms.CharField(
        required=True, max_length=255, label='Name (Vorname)',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={
            'required': 'Name is required.',
            'max_length': 'Name must be at most 255 characters.'
        }
    )
    block2_patient__patiant_street = forms.CharField(
        required=False, max_length=255, label='Street',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Street must be at most 255 characters.'}
    )
    block2_patient__patiant_zip = forms.CharField(
        required=False, max_length=20, label='ZIP',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'ZIP must be at most 20 characters.'}
    )
    block2_patient__patiant_city = forms.CharField(
        required=False, max_length=255, label='City',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'City must be at most 255 characters.'}
    )
    block2_patient__patiant_country = forms.CharField(
        required=False, max_length=50, label='Country',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Country must be at most 50 characters.'}
    )
    block2_patient__geb_am = forms.CharField(
        required=False, max_length=20, label='Birth Date (geb. am)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DD.MM.YY'}),
        error_messages={'max_length': 'Birth date must be at most 20 characters.'}
    )
    block2_patient__kostentraegerkennung = forms.CharField(
        required=False, max_length=50, label='Kostentraegerkennung',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Kostentraegerkennung must be at most 50 characters.'}
    )
    block2_patient__versichertennr = forms.CharField(
        required=False, max_length=50, label='Versichertennr.',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Versichertennr. must be at most 50 characters.'}
    )
    
    # Block 3: Doctor IDs
    block3_doctor_ids__betriebsstaetten_nr = forms.CharField(
        required=False, max_length=50, label='Betriebsstaetten Nr.',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Betriebsstaetten Nr. must be at most 50 characters.'}
    )
    block3_doctor_ids__arzt_nr = forms.CharField(
        required=False, max_length=50, label='Arzt Nr.',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Arzt Nr. must be at most 50 characters.'}
    )
    block3_doctor_ids__datum = forms.CharField(
        required=False, max_length=20, label='Datum',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DD.MM.YY'}),
        error_messages={'max_length': 'Datum must be at most 20 characters.'}
    )
    
    # Block 4: Reasons
    block4_reasons__unfall = forms.BooleanField(
        required=False, label='Unfall',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block4_reasons__arbeitsunfall = forms.BooleanField(
        required=False, label='Arbeitsunfall',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block4_reasons__versorgungsleiden = forms.BooleanField(
        required=False, label='Versorgungsleiden',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Block 5: Directions
    block5_directions__hinfahrt = forms.BooleanField(
        required=False, label='Hinfahrt',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block5_directions__rueckfahrt = forms.BooleanField(
        required=False, label='Rueckfahrt',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Block 6: Treatment Type
    block6_treatment_type__voll_teilstationaer = forms.BooleanField(
        required=False, label='Voll-/Teilstationaer',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block6_treatment_type__vor_nachstationaer = forms.BooleanField(
        required=False, label='Vor-/Nachstationaer',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block6_treatment_type__ambulant_merkmale = forms.BooleanField(
        required=False, label='Ambulant Merkmale',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block6_treatment_type__anderer_grund = forms.BooleanField(
        required=False, label='Anderer Grund',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Block 7: Mandatory Trips
    block7_mandatory_trips__hochfrequent = forms.BooleanField(
        required=False, label='Hochfrequent',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block7_mandatory_trips__ausnahmefall = forms.BooleanField(
        required=False, label='Ausnahmefall',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block7_mandatory_trips__dauerhafte_mobilitaet = forms.BooleanField(
        required=False, label='Dauerhafte Mobilitaet',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Block 8: KTW Reason
    block8_ktw_reason__anderer_grund_ktw = forms.BooleanField(
        required=False, label='Anderer Grund KTW',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block8_ktw_reason__reason_description = forms.CharField(
        required=False, max_length=500, label='Reason Description',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Reason description must be at most 500 characters.'}
    )
    
    # Block 9: Schedule
    block9_schedule__vom_am = forms.CharField(
        required=False, max_length=20, label='Vom/Am',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DD.MM.YY'}),
        error_messages={'max_length': 'Vom/Am must be at most 20 characters.'}
    )
    block9_schedule__x_pro_woche = forms.CharField(
        required=False, max_length=20, label='X pro Woche',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'X pro Woche must be at most 20 characters.'}
    )
    block9_schedule__bis_voraussichtlich = forms.CharField(
        required=False, max_length=20, label='Bis voraussichtlich',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DD.MM.YY'}),
        error_messages={'max_length': 'Bis voraussichtlich must be at most 20 characters.'}
    )
    
    # Block 10: Clinic
    block10_clinic__clinic_name = forms.CharField(
        required=False, max_length=255, label='Clinic Name',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Clinic name must be at most 255 characters.'}
    )
    block10_clinic__clinic_street = forms.CharField(
        required=False, max_length=255, label='Street',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Clinic street must be at most 255 characters.'}
    )
    block10_clinic__clinic_zip = forms.CharField(
        required=False, max_length=20, label='ZIP',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Clinic ZIP must be at most 20 characters.'}
    )
    block10_clinic__clinic_city = forms.CharField(
        required=False, max_length=255, label='City',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Clinic city must be at most 255 characters.'}
    )
    
    # Block 11: Transport Type
    block11_transport_type__taxi_mietwagen = forms.BooleanField(
        required=False, label='Taxi/Mietwagen',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block11_transport_type__ktw_medizinisch = forms.BooleanField(
        required=False, label='KTW (medizinisch)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block11_transport_type__vitalzeichenkontrolle = forms.BooleanField(
        required=False, label='Vitalzeichenkontrolle',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block11_transport_type__rtw = forms.BooleanField(
        required=False, label='RTW',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block11_transport_type__naw_nef = forms.BooleanField(
        required=False, label='NAW/NEF',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block11_transport_type__andere = forms.BooleanField(
        required=False, label='Andere',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Block 12: Transport Mode
    block12_transport_mode__rollstuhl = forms.BooleanField(
        required=False, label='Rollstuhl',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block12_transport_mode__tragestuhl = forms.BooleanField(
        required=False, label='Tragestuhl',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    block12_transport_mode__liegend = forms.BooleanField(
        required=False, label='Liegend',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Block 13: Doctor Contact
    block13_doctor_contact__auftraggeberName = forms.CharField(
        required=False, max_length=255, label='Auftraggeber Name',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Auftraggeber name must be at most 255 characters.'}
    )
    block13_doctor_contact__auftraggeberInfo = forms.CharField(
        required=False, max_length=1000, label='Auftraggeber Info',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        error_messages={'max_length': 'Auftraggeber info must be at most 1000 characters.'}
    )
    block13_doctor_contact__auftraggeberZip = forms.CharField(
        required=False, max_length=20, label='ZIP',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Auftraggeber ZIP must be at most 20 characters.'}
    )
    block13_doctor_contact__auftraggeberCity = forms.CharField(
        required=False, max_length=255, label='City',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Auftraggeber city must be at most 255 characters.'}
    )
    block13_doctor_contact__auftraggeberTelefon = forms.CharField(
        required=False, max_length=50, label='Telefon',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={'max_length': 'Auftraggeber telefon must be at most 50 characters.'}
    )
    
    # Block 14: Notes
    block14_notes__begruendung_sonstiges = forms.CharField(
        required=False, max_length=2000, label='Begruendung Sonstiges',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        error_messages={'max_length': 'Begruendung Sonstiges must be at most 2000 characters.'}
    )

    def to_parsed_data(self):
        """Convert cleaned form data back to nested JSON structure."""
        data = self.cleaned_data
        parsed = {
            'block1_insurance': {},
            'block2_patient': {},
            'block3_doctor_ids': {},
            'block4_reasons': {},
            'block5_directions': {},
            'block6_treatment_type': {},
            'block7_mandatory_trips': {},
            'block8_ktw_reason': {},
            'block9_schedule': {},
            'block10_clinic': {},
            'block11_transport_type': {},
            'block12_transport_mode': {},
            'block13_doctor_contact': {},
            'block14_notes': {},
        }
        for key, value in data.items():
            if '__' in key:
                block, field = key.split('__', 1)
                if block in parsed:
                    parsed[block][field] = value
        return parsed

    @classmethod
    def from_parsed_data(cls, parsed_data):
        """Create form initial data from nested JSON structure."""
        initial = {}
        if not parsed_data:
            return initial
        for block_name, block_data in parsed_data.items():
            if isinstance(block_data, dict):
                for field_name, value in block_data.items():
                    key = f"{block_name}__{field_name}"
                    initial[key] = value
        return initial
