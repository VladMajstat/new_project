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
        
        # Map parsed_data blocks to model fields
        initial = {}
        
        # Block 1: Insurance
        b1 = parsed_data.get('block1_insurance', {})
        initial['krankenkasse'] = b1.get('krankenkasse', '')
        initial['insurance_status'] = b1.get('status', '')
        
        # Block 2: Patient
        b2 = parsed_data.get('block2_patient', {})
        initial['patient_surname'] = b2.get('patiant_surname', '')
        initial['patient_name'] = b2.get('patiant_name', '')
        initial['patient_street'] = b2.get('patiant_street', '')
        initial['patient_zip'] = b2.get('patiant_zip', '')
        initial['patient_city'] = b2.get('patiant_city', '')
        initial['patient_country'] = b2.get('patiant_country', 'D')
        initial['patient_birthday'] = b2.get('geb_am', '')
        initial['kostentraegerkennung'] = b2.get('kostentraegerkennung', '')
        initial['versichertennr'] = b2.get('versichertennr', '')
        
        # Block 3: Doctor IDs
        b3 = parsed_data.get('block3_doctor_ids', {})
        initial['betriebsstaetten_nr'] = b3.get('betriebsstaetten_nr', '')
        initial['arzt_nr'] = b3.get('arzt_nr', '')
        initial['datum'] = b3.get('datum', '')
        
        # Block 4: Reasons
        b4 = parsed_data.get('block4_reasons', {})
        initial['unfall'] = b4.get('unfall', False)
        initial['arbeitsunfall'] = b4.get('arbeitsunfall', False)
        initial['versorgungsleiden'] = b4.get('versorgungsleiden', False)
        
        # Block 5: Direction
        b5 = parsed_data.get('block5_directions', {})
        initial['hinfahrt'] = b5.get('hinfahrt', True)
        initial['rueckfahrt'] = b5.get('rueckfahrt', True)
        
        # Block 6: Treatment
        b6 = parsed_data.get('block6_treatment_type', {})
        initial['voll_teilstationaer'] = b6.get('voll_teilstationaer', False)
        initial['vor_nachstationaer'] = b6.get('vor_nachstationaer', False)
        initial['ambulant_merkmale'] = b6.get('ambulant_merkmale', False)
        initial['anderer_grund'] = b6.get('anderer_grund', False)
        
        # Block 7: Mandatory trips
        b7 = parsed_data.get('block7_mandatory_trips', {})
        initial['hochfrequent'] = b7.get('hochfrequent', False)
        initial['ausnahmefall'] = b7.get('ausnahmefall', False)
        initial['dauerhafte_mobilitaet'] = b7.get('dauerhafte_mobilitaet', False)
        
        # Block 8: KTW
        b8 = parsed_data.get('block8_ktw_reason', {})
        initial['anderer_grund_ktw'] = b8.get('anderer_grund_ktw', False)
        initial['reason_description'] = b8.get('reason_description', '')
        
        # Block 9: Schedule
        b9 = parsed_data.get('block9_schedule', {})
        initial['vom_am'] = b9.get('vom_am', '')
        initial['x_pro_woche'] = b9.get('x_pro_woche', '')
        initial['bis_voraussichtlich'] = b9.get('bis_voraussichtlich', '')
        
        # Block 10: Clinic
        b10 = parsed_data.get('block10_clinic', {})
        initial['clinic_name'] = b10.get('clinic_name', '')
        initial['clinic_street'] = b10.get('clinic_street', '')
        initial['clinic_zip'] = b10.get('clinic_zip', '')
        initial['clinic_city'] = b10.get('clinic_city', '')
        
        # Block 11: Transport type
        b11 = parsed_data.get('block11_transport_type', {})
        initial['taxi_mietwagen'] = b11.get('taxi_mietwagen', False)
        initial['ktw_medizinisch'] = b11.get('ktw_medizinisch', False)
        initial['vitalzeichenkontrolle'] = b11.get('vitalzeichenkontrolle', False)
        initial['rtw'] = b11.get('rtw', False)
        initial['naw_nef'] = b11.get('naw_nef', False)
        initial['andere_transport'] = b11.get('andere', False)
        
        # Block 12: Transport mode
        b12 = parsed_data.get('block12_transport_mode', {})
        initial['rollstuhl'] = b12.get('rollstuhl', False)
        initial['tragestuhl'] = b12.get('tragestuhl', False)
        initial['liegend'] = b12.get('liegend', False)
        
        # Block 13: Doctor contact
        b13 = parsed_data.get('block13_doctor_contact', {})
        initial['auftraggeber_name'] = b13.get('auftraggeberName', '')
        initial['auftraggeber_info'] = b13.get('auftraggeberInfo', '')
        initial['auftraggeber_zip'] = b13.get('auftraggeberZip', '')
        initial['auftraggeber_city'] = b13.get('auftraggeberCity', '')
        initial['auftraggeber_telefon'] = b13.get('auftraggeberTelefon', '')
        
        # Block 14: Notes
        b14 = parsed_data.get('block14_notes', {})
        initial['begruendung_sonstiges'] = b14.get('begruendung_sonstiges', '')
        
        return cls(initial=initial)
    
    def to_parsed_data(self):
        """Convert form data back to nested JSON structure for Dispolive."""
        data = self.cleaned_data
        return {
            'block1_insurance': {
                'krankenkasse': data.get('krankenkasse', ''),
                'status': data.get('insurance_status', ''),
            },
            'block2_patient': {
                'patiant_surname': data.get('patient_surname', ''),
                'patiant_name': data.get('patient_name', ''),
                'patiant_street': data.get('patient_street', ''),
                'patiant_zip': data.get('patient_zip', ''),
                'patiant_city': data.get('patient_city', ''),
                'patiant_country': data.get('patient_country', 'D'),
                'geb_am': data.get('patient_birthday', ''),
                'kostentraegerkennung': data.get('kostentraegerkennung', ''),
                'versichertennr': data.get('versichertennr', ''),
            },
            'block3_doctor_ids': {
                'betriebsstaetten_nr': data.get('betriebsstaetten_nr', ''),
                'arzt_nr': data.get('arzt_nr', ''),
                'datum': data.get('datum', ''),
            },
            'block4_reasons': {
                'unfall': data.get('unfall', False),
                'arbeitsunfall': data.get('arbeitsunfall', False),
                'versorgungsleiden': data.get('versorgungsleiden', False),
            },
            'block5_directions': {
                'hinfahrt': data.get('hinfahrt', True),
                'rueckfahrt': data.get('rueckfahrt', True),
            },
            'block6_treatment_type': {
                'voll_teilstationaer': data.get('voll_teilstationaer', False),
                'vor_nachstationaer': data.get('vor_nachstationaer', False),
                'ambulant_merkmale': data.get('ambulant_merkmale', False),
                'anderer_grund': data.get('anderer_grund', False),
            },
            'block7_mandatory_trips': {
                'hochfrequent': data.get('hochfrequent', False),
                'ausnahmefall': data.get('ausnahmefall', False),
                'dauerhafte_mobilitaet': data.get('dauerhafte_mobilitaet', False),
            },
            'block8_ktw_reason': {
                'anderer_grund_ktw': data.get('anderer_grund_ktw', False),
                'reason_description': data.get('reason_description', ''),
            },
            'block9_schedule': {
                'vom_am': data.get('vom_am', ''),
                'x_pro_woche': data.get('x_pro_woche', ''),
                'bis_voraussichtlich': data.get('bis_voraussichtlich', ''),
            },
            'block10_clinic': {
                'clinic_name': data.get('clinic_name', ''),
                'clinic_street': data.get('clinic_street', ''),
                'clinic_zip': data.get('clinic_zip', ''),
                'clinic_city': data.get('clinic_city', ''),
            },
            'block11_transport_type': {
                'taxi_mietwagen': data.get('taxi_mietwagen', False),
                'ktw_medizinisch': data.get('ktw_medizinisch', False),
                'vitalzeichenkontrolle': data.get('vitalzeichenkontrolle', False),
                'rtw': data.get('rtw', False),
                'naw_nef': data.get('naw_nef', False),
                'andere': data.get('andere_transport', False),
            },
            'block12_transport_mode': {
                'rollstuhl': data.get('rollstuhl', False),
                'tragestuhl': data.get('tragestuhl', False),
                'liegend': data.get('liegend', False),
            },
            'block13_doctor_contact': {
                'auftraggeberName': data.get('auftraggeber_name', ''),
                'auftraggeberInfo': data.get('auftraggeber_info', ''),
                'auftraggeberZip': data.get('auftraggeber_zip', ''),
                'auftraggeberCity': data.get('auftraggeber_city', ''),
                'auftraggeberTelefon': data.get('auftraggeber_telefon', ''),
            },
            'block14_notes': {
                'begruendung_sonstiges': data.get('begruendung_sonstiges', ''),
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
