from django.db import models
from django.conf import settings


class DispoliveReport(models.Model):
    """
    Main model for Dispolive API data structure.
    Form fields and validation are derived from this model (DRY).
    """
    
    # === Display Settings ===
    show_form = models.BooleanField(default=True, verbose_name="Show form")
    show_only_filled = models.BooleanField(default=False, verbose_name="Form: only filled fields")
    
    # === Patient (required) ===
    patient_surname = models.CharField(
        max_length=100,
        verbose_name="Patient surname",
        error_messages={
            'required': 'Patient surname is required.',
            'max_length': 'Patient surname must not exceed 100 characters.',
        },
    )
    patient_name = models.CharField(
        max_length=100,
        verbose_name="Patient first name",
        error_messages={
            'required': 'Patient first name is required.',
            'max_length': 'Patient first name must not exceed 100 characters.',
        },
    )
    patient_street = models.CharField(max_length=255, blank=True, default="", verbose_name="Patient street")
    patient_zip = models.CharField(max_length=10, blank=True, default="", verbose_name="Patient ZIP")
    patient_city = models.CharField(max_length=100, blank=True, default="", verbose_name="Patient city")
    patient_country = models.CharField(max_length=50, blank=True, default="D", verbose_name="Patient country")
    patient_birthday = models.CharField(max_length=20, blank=True, default="", verbose_name="Patient birth date")
    patient_telephone = models.CharField(max_length=30, blank=True, default="", verbose_name="Patient phone")
    
    # === Insurance ===
    krankenkasse = models.CharField(max_length=255, blank=True, default="", verbose_name="Insurer (Krankenkasse)")
    kostentraegerkennung = models.CharField(max_length=50, blank=True, default="", verbose_name="Cost carrier code")
    versichertennr = models.CharField(max_length=50, blank=True, default="", verbose_name="Insurance number")
    insurance_status = models.CharField(max_length=20, blank=True, default="", verbose_name="Insurance status")
    
    # === Doctor IDs ===
    betriebsstaetten_nr = models.CharField(max_length=50, blank=True, default="", verbose_name="Facility ID")
    arzt_nr = models.CharField(max_length=50, blank=True, default="", verbose_name="Doctor ID")
    datum = models.CharField(max_length=20, blank=True, default="", verbose_name="Prescription date")
    
    # === Reasons (checkboxes) ===
    unfall = models.BooleanField(default=False, verbose_name="Reason: accident")
    arbeitsunfall = models.BooleanField(default=False, verbose_name="Reason: work accident")
    versorgungsleiden = models.BooleanField(default=False, verbose_name="Reason: care condition")
    
    # === Direction ===
    hinfahrt = models.BooleanField(default=True, verbose_name="Outbound trip")
    rueckfahrt = models.BooleanField(default=True, verbose_name="Return trip")
    
    # === Treatment type ===
    voll_teilstationaer = models.BooleanField(default=False, verbose_name="Treatment: inpatient full/partial")
    vor_nachstationaer = models.BooleanField(default=False, verbose_name="Treatment: pre/post inpatient")
    ambulant_merkmale = models.BooleanField(default=False, verbose_name="Treatment: outpatient markers")
    anderer_grund = models.BooleanField(default=False, verbose_name="Treatment: other reason")
    
    # === Mandatory trips ===
    hochfrequent = models.BooleanField(default=False, verbose_name="Mandatory trip: high frequency")
    ausnahmefall = models.BooleanField(default=False, verbose_name="Mandatory trip: exceptional case")
    dauerhafte_mobilitaet = models.BooleanField(default=False, verbose_name="Mandatory trip: permanent mobility issues")
    
    # === KTW Reason ===
    anderer_grund_ktw = models.BooleanField(default=False, verbose_name="KTW reason: other")
    reason_description = models.CharField(max_length=500, blank=True, default="", verbose_name="KTW reason details")
    
    # === Schedule ===
    vom_am = models.CharField(max_length=20, blank=True, default="", verbose_name="Schedule: valid from")
    x_pro_woche = models.CharField(max_length=10, blank=True, default="", verbose_name="Schedule: times per week")
    bis_voraussichtlich = models.CharField(max_length=20, blank=True, default="", verbose_name="Schedule: valid until")
    
    # === Clinic ===
    clinic_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Destination: clinic name")
    clinic_street = models.CharField(max_length=255, blank=True, default="", verbose_name="Destination: clinic street")
    clinic_zip = models.CharField(max_length=10, blank=True, default="", verbose_name="Destination: clinic ZIP")
    clinic_city = models.CharField(max_length=100, blank=True, default="", verbose_name="Destination: clinic city")
    
    # === Transport type ===
    taxi_mietwagen = models.BooleanField(default=False, verbose_name="Transport type: taxi/rental car")
    ktw_medizinisch = models.BooleanField(default=False, verbose_name="Transport type: KTW (medical)")
    vitalzeichenkontrolle = models.BooleanField(default=False, verbose_name="Transport type: vital monitoring")
    rtw = models.BooleanField(default=False, verbose_name="Transport type: RTW")
    naw_nef = models.BooleanField(default=False, verbose_name="Transport type: NAW/NEF")
    andere_transport = models.BooleanField(default=False, verbose_name="Transport type: other")
    
    # === Transport mode ===
    rollstuhl = models.BooleanField(default=False, verbose_name="Position: wheelchair")
    tragestuhl = models.BooleanField(default=False, verbose_name="Position: carry chair")
    liegend = models.BooleanField(default=False, verbose_name="Position: lying")
    
    # === Doctor contact ===
    auftraggeber_name = models.CharField(max_length=255, blank=True, default="", verbose_name="Ordering party name")
    auftraggeber_info = models.TextField(blank=True, default="", verbose_name="Ordering party info")
    auftraggeber_zip = models.CharField(max_length=10, blank=True, default="", verbose_name="Ordering party ZIP")
    auftraggeber_city = models.CharField(max_length=100, blank=True, default="", verbose_name="Ordering party city")
    auftraggeber_telefon = models.CharField(max_length=30, blank=True, default="", verbose_name="Ordering party phone")
    
    # === Notes ===
    begruendung_sonstiges = models.TextField(blank=True, default="", verbose_name="Notes / justification")
    
    # === Metadata ===
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Dispolive Report"
        verbose_name_plural = "Dispolive Reports"
    
    def __str__(self):
        return f"{self.patient_surname} {self.patient_name}"


class DocumentUpload(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='uploaded_documents')
    file = models.FileField(upload_to='uploads/pdfs/')
    original_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    extracted_text = models.TextField(blank=True, default="")
    parsed_data = models.JSONField(null=True, blank=True)
    processing_status = models.CharField(
        max_length=20,
        default="uploaded",
        choices=[
            ("uploaded", "uploaded"),
            ("processing", "processing"),
            ("pending_review", "pending_review"),
            ("done", "done"),
            ("error", "error"),
        ],
    )
    dispolive_payload = models.JSONField(null=True, blank=True)
    dispolive_report = models.OneToOneField(
        DispoliveReport, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='document')

    processing_error = models.TextField(blank=True, default="")

    def save(self, *args, **kwargs):
        if self.file and not self.original_name:
            self.original_name = self.file.name
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.original_name or "Unnamed Document"

class DocumentPhoto(models.Model):
    document = models.ForeignKey(DocumentUpload, on_delete=models.CASCADE, related_name='photos')
    photo = models.ImageField(upload_to='document_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
class DocumentPhoto(models.Model):
    document = models.ForeignKey(DocumentUpload, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='document_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Photo for {self.document.id}"
    def __str__(self):
        return f"Photo for {self.document.id}"
