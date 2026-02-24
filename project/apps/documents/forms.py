from django import forms
from .models import DispoliveReport, DocumentPhoto
from .services.photo_processor import PhotoProcessor


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


class DispoliveReportForm(forms.ModelForm):
    """
    ModelForm for DispoliveReport - DRY approach.
    All fields, validation, and error messages derived from model.
    """
    
    class Meta:
        model = DispoliveReport
        fields = '__all__'
        widgets = {
            # Display settings
            'show_form': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_only_filled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Patient
            'patient_surname': forms.TextInput(attrs={'class': 'form-control'}),
            'patient_name': forms.TextInput(attrs={'class': 'form-control'}),
            'patient_street': forms.TextInput(attrs={'class': 'form-control'}),
            'patient_zip': forms.TextInput(attrs={'class': 'form-control'}),
            'patient_city': forms.TextInput(attrs={'class': 'form-control'}),
            'patient_country': forms.TextInput(attrs={'class': 'form-control'}),
            'patient_birthday': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DD.MM.YY'}),
            'patient_telephone': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Insurance
            'krankenkasse': forms.TextInput(attrs={'class': 'form-control'}),
            'kostentraegerkennung': forms.TextInput(attrs={'class': 'form-control'}),
            'versichertennr': forms.TextInput(attrs={'class': 'form-control'}),
            'insurance_status': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Doctor IDs
            'betriebsstaetten_nr': forms.TextInput(attrs={'class': 'form-control'}),
            'arzt_nr': forms.TextInput(attrs={'class': 'form-control'}),
            'datum': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DD.MM.YY'}),
            
            # Checkboxes - Reasons
            'unfall': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'arbeitsunfall': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'versorgungsleiden': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Checkboxes - Direction
            'hinfahrt': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'rueckfahrt': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Checkboxes - Treatment
            'voll_teilstationaer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'vor_nachstationaer': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ambulant_merkmale': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'anderer_grund': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Checkboxes - Mandatory trips
            'hochfrequent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ausnahmefall': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dauerhafte_mobilitaet': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # KTW
            'anderer_grund_ktw': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reason_description': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Schedule
            'vom_am': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DD.MM.YY'}),
            'x_pro_woche': forms.TextInput(attrs={'class': 'form-control'}),
            'bis_voraussichtlich': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'DD.MM.YY'}),
            
            # Clinic
            'clinic_name': forms.TextInput(attrs={'class': 'form-control'}),
            'clinic_street': forms.TextInput(attrs={'class': 'form-control'}),
            'clinic_zip': forms.TextInput(attrs={'class': 'form-control'}),
            'clinic_city': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Transport type
            'taxi_mietwagen': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ktw_medizinisch': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'vitalzeichenkontrolle': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'rtw': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'naw_nef': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'andere_transport': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Transport mode
            'rollstuhl': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tragestuhl': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'liegend': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            # Doctor contact
            'auftraggeber_name': forms.TextInput(attrs={'class': 'form-control'}),
            'auftraggeber_info': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'auftraggeber_zip': forms.TextInput(attrs={'class': 'form-control'}),
            'auftraggeber_city': forms.TextInput(attrs={'class': 'form-control'}),
            'auftraggeber_telefon': forms.TextInput(attrs={'class': 'form-control'}),
            
            # Notes
            'begruendung_sonstiges': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add is-invalid class to fields with errors
        if self.is_bound:
            for field_name, field in self.fields.items():
                if field_name in self.errors:
                    classes = field.widget.attrs.get('class', '').split()
                    if 'is-invalid' not in classes:
                        classes.append('is-invalid')
                    field.widget.attrs['class'] = ' '.join(filter(None, classes))
    
    @classmethod
    def from_parsed_data(cls, parsed_data):
        """Create form instance from parsed JSON data."""
        if not parsed_data:
            return cls()

        data = parsed_data.get('data', {}) if isinstance(parsed_data, dict) else {}
        initial = {}

        # Insurance
        initial['krankenkasse'] = data.get('insurance_name', '')
        initial['insurance_status'] = data.get('status_number', '')
        initial['kostentraegerkennung'] = data.get('kostentraegerkennung', '')
        initial['versichertennr'] = data.get('insurance_number', '')

        # Patient
        initial['patient_surname'] = data.get('patient_last_name', '')
        initial['patient_name'] = data.get('patient_first_name', '')
        initial['patient_street'] = data.get('patient_street', '')
        initial['patient_zip'] = data.get('patient_zip', '')
        initial['patient_city'] = data.get('patient_city', '')
        initial['patient_country'] = 'D'
        initial['patient_birthday'] = data.get('patient_birth_date', '')
        initial['patient_telephone'] = ''

        # Doctor IDs
        initial['betriebsstaetten_nr'] = data.get('betriebsstaetten_nr', '')
        initial['arzt_nr'] = data.get('arzt_nr', '')
        initial['datum'] = data.get('prescription_date', '')

        # Direction
        initial['hinfahrt'] = data.get('transport_outbound', False)
        initial['rueckfahrt'] = data.get('transport_return', False)

        # Top-right reasons
        initial['unfall'] = data.get('reason_accident', False)
        initial['arbeitsunfall'] = data.get('reason_work_accident', False)
        initial['versorgungsleiden'] = data.get('reason_care_condition', False)

        # Treatment reasons (mapped to existing form fields)
        initial['voll_teilstationaer'] = data.get('reason_full_or_partial_inpatient', False)
        initial['vor_nachstationaer'] = data.get('reason_pre_post_inpatient', False)
        initial['ambulant_merkmale'] = data.get('reason_ambulatory_with_marker', False)
        initial['anderer_grund'] = data.get('reason_other', False)

        # Mandatory trips
        initial['hochfrequent'] = data.get('reason_high_frequency', False)
        initial['dauerhafte_mobilitaet'] = data.get('reason_mobility_impairment_6m', False)

        # KTW
        initial['anderer_grund_ktw'] = data.get('reason_other_ktw', False)
        initial['reason_description'] = data.get('ktw_reason_text', '')

        # Schedule
        initial['vom_am'] = data.get('treatment_date_from', '')
        initial['x_pro_woche'] = data.get('treatment_frequency_per_week', '')
        initial['bis_voraussichtlich'] = data.get('treatment_until', '')

        # Clinic
        initial['clinic_name'] = data.get('treatment_location_name', '')
        initial['clinic_city'] = data.get('treatment_location_city', '')
        initial['clinic_street'] = data.get('treatment_location_street', '')
        initial['clinic_zip'] = data.get('treatment_location_zip', '')

        # Transport type
        initial['taxi_mietwagen'] = False  # taxi not allowed
        initial['ktw_medizinisch'] = data.get('transport_ktw', False)
        initial['rtw'] = data.get('transport_rtw', False)
        initial['naw_nef'] = data.get('transport_naw_nef', False)
        initial['andere_transport'] = data.get('transport_other', False)
        initial['vitalzeichenkontrolle'] = False

        # Transport mode
        initial['rollstuhl'] = data.get('equipment_wheelchair', False)
        initial['tragestuhl'] = data.get('equipment_transport_chair', False)
        initial['liegend'] = data.get('equipment_lying', False)

        # Doctor contact (not in new schema)
        initial['auftraggeber_name'] = data.get('ordering_party_name', '')
        initial['auftraggeber_info'] = data.get('ordering_party_info', '')
        initial['auftraggeber_zip'] = data.get('ordering_party_zip', '')
        initial['auftraggeber_city'] = data.get('ordering_party_city', '')
        initial['auftraggeber_telefon'] = data.get('ordering_party_phone', '')

        # Notes
        initial['begruendung_sonstiges'] = ''

        return cls(initial=initial)
    
    def to_parsed_data(self):
        """Convert form data back to JSON structure for Dispolive."""
        data = self.cleaned_data
        return {
            'data': {
                'insurance_name': data.get('krankenkasse', ''),
                'patient_last_name': data.get('patient_surname', ''),
                'patient_first_name': data.get('patient_name', ''),
                'patient_birth_date': data.get('patient_birthday', ''),
                'patient_street': data.get('patient_street', ''),
                'patient_zip': data.get('patient_zip', ''),
                'patient_city': data.get('patient_city', ''),
                'kostentraegerkennung': data.get('kostentraegerkennung', ''),
                'insurance_number': data.get('versichertennr', ''),
                'status_number': data.get('insurance_status', ''),
                'betriebsstaetten_nr': data.get('betriebsstaetten_nr', ''),
                'arzt_nr': data.get('arzt_nr', ''),
                'prescription_date': data.get('datum', ''),
                'transport_outbound': data.get('hinfahrt', False),
                'transport_return': data.get('rueckfahrt', False),
                'reason_full_or_partial_inpatient': data.get('voll_teilstationaer', False),
                'reason_pre_post_inpatient': data.get('vor_nachstationaer', False),
                'reason_ambulatory_with_marker': data.get('ambulant_merkmale', False),
                'reason_other': data.get('anderer_grund', False),
                'reason_high_frequency': data.get('hochfrequent', False),
                'reason_mobility_impairment_6m': data.get('dauerhafte_mobilitaet', False),
                'reason_other_ktw': data.get('anderer_grund_ktw', False),
                'treatment_date_from': data.get('vom_am', ''),
                'treatment_frequency_per_week': data.get('x_pro_woche', ''),
                'treatment_until': data.get('bis_voraussichtlich', ''),
                'treatment_location_name': data.get('clinic_name', ''),
                'treatment_location_city': data.get('clinic_city', ''),
                'transport_taxi': data.get('taxi_mietwagen', False),
                'transport_ktw': data.get('ktw_medizinisch', False),
                'transport_rtw': data.get('rtw', False),
                'transport_naw_nef': data.get('naw_nef', False),
                'transport_other': data.get('andere_transport', False),
                'equipment_wheelchair': data.get('rollstuhl', False),
                'equipment_transport_chair': data.get('tragestuhl', False),
                'equipment_lying': data.get('liegend', False),
                'medical_reason_text': data.get('begruendung_sonstiges', ''),
            },
        }


# Alias for backward compatibility

ReviewForm = DispoliveReportForm


class DocumentPhotoForm(forms.ModelForm):
    """Form for uploading document photos via mobile camera"""
    
    class Meta:
        model = DocumentPhoto
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={
                'accept': 'image/*',
                'class': 'photo-input',
                'id': 'photo-input'
            })
        }
    
    def clean_image(self):
        image = self.cleaned_data.get('image')
        
        if not image:
            raise forms.ValidationError('No image provided')
        
        # Validate photo
        is_valid, error_msg = PhotoProcessor.validate_photo(image)
        if not is_valid:
            raise forms.ValidationError(error_msg)
        
        # Process photo (EXIF correction, optimization)
        try:
            processed_image = PhotoProcessor.process_photo(image)
            return processed_image
        except ValueError as e:
            raise forms.ValidationError(str(e))
