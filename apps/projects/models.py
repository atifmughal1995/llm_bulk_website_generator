from django.db import models


class Project(models.Model):
    """Represents a project with its configuration and generated pages."""

    name = models.CharField(max_length=100, unique=True)
    service_type = models.CharField(max_length=500, blank=True, null=True)
    homepage_template = models.ForeignKey(
        'Template',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='project_homepage_template',
    )
    service_page_template = models.ForeignKey(
        'Template',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='project_service_page_template',
    )
    homepage_ai_response = models.TextField(blank=True, null=True)
    images = models.TextField(blank=True, null=True)
    prompt = models.TextField(blank=True, null=True)
    tracking_code_head = models.TextField(blank=True, default='')
    tracking_code_body = models.TextField(blank=True, default='')
    base_html = models.TextField(blank=True, null=True)
    client_domain = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='Custom domain configured for the project',
    )
    netlify_site_id = models.CharField(max_length=100, blank=True, null=True)
    netlify_site_url = models.CharField(max_length=100, blank=True, null=True)
    emailjs_public_key = models.CharField(max_length=100, blank=True, null=True)
    emailjs_service_id = models.CharField(max_length=100, blank=True, null=True)
    emailjs_template_id = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    status = models.CharField(max_length=100, blank=True, null=True)
    model = models.CharField(
        max_length=20,
        choices=[
            ('openai', 'OpenAI'),
            ('anthropic', 'Anthropic (Claude)'),
        ],
        default='anthropic',
    )
    scripts = models.TextField(blank=True, null=True)
    contact_phone_number = models.CharField(max_length=100, default='', blank=True, null=True)
    netlify_site_url_history = models.TextField(blank=True, default='')

    def __str__(self) -> str:
        return self.name


class ProjectPage(models.Model):
    """A page belonging to a project, such as a service page or homepage."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='pages')
    name = models.CharField(max_length=100)
    slug = models.CharField(blank=True, null=True, max_length=100)
    type = models.CharField(blank=True, null=True, max_length=100)
    ai_response = models.TextField(blank=True, null=True)
    complete_html = models.TextField(blank=True, null=True)
    content_html = models.TextField(blank=True, null=True)
    meta_tags = models.TextField(default='', blank=True, null=True)
    status = models.CharField(max_length=100, default='', blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Project Pages'

    def __str__(self) -> str:
        return self.name


class ProjectPageVersion(models.Model):
    """Version snapshot of a project page's complete HTML."""

    project_page = models.ForeignKey(
        ProjectPage, on_delete=models.CASCADE, related_name='versions'
    )
    complete_html = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = 'Project Pages Versions'

    def __str__(self) -> str:
        return self.project_page.name


class ProjectPromptHistory(models.Model):
    """History of prompts and their generated HTML for a project."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='prompts')
    complete_html = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    prompt = models.CharField(max_length=10000)

    class Meta:
        verbose_name_plural = 'Project Prompts History'

    def __str__(self) -> str:
        return self.project.name


class State(models.Model):
    """A US state associated with a project."""

    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=10)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='states')

    def __str__(self) -> str:
        return f'{self.name}, {self.abbreviation}'


class County(models.Model):
    """A county within a state."""

    name = models.CharField(max_length=100)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='counties')

    class Meta:
        unique_together = ('name', 'state')
        verbose_name_plural = 'Counties'

    def __str__(self) -> str:
        return self.name


class City(models.Model):
    """A city within a county, with AI-generated content."""

    name = models.CharField(max_length=100)
    county = models.ForeignKey(County, on_delete=models.CASCADE, related_name='cities')
    prompt = models.TextField(blank=True, null=True)
    ai_response = models.TextField(blank=True, null=True)
    complete_html = models.TextField(blank=True, null=True)
    content_html = models.TextField(blank=True, null=True)
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    meta_tags = models.TextField(default='', blank=True, null=True)

    class Meta:
        unique_together = ('name', 'county')
        verbose_name_plural = 'Cities'

    def __str__(self) -> str:
        return self.name


class CityPromptHistory(models.Model):
    """History of prompts and their generated HTML for a city."""

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='prompts')
    complete_html = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    prompt = models.CharField(max_length=10000)

    class Meta:
        verbose_name_plural = 'City Prompts History'

    def __str__(self) -> str:
        return self.prompt


class CityPageVersions(models.Model):
    """Version snapshot of a city page's complete HTML."""

    city_page = models.ForeignKey(City, on_delete=models.CASCADE, related_name='versions')
    complete_html = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = 'City Pages Versions'

    def __str__(self) -> str:
        return self.city_page.name


class Page(models.Model):
    """A service page with AI-generated content."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    template = models.ForeignKey(
        'Template', on_delete=models.CASCADE, blank=True, null=True, related_name='templates'
    )
    temperature = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    prompt = models.TextField(blank=True, null=True)
    ai_response = models.TextField(blank=True, null=True)
    zip_code = models.CharField(max_length=50, blank=True, null=True)
    city = models.ForeignKey(
        City, on_delete=models.CASCADE, null=True, blank=True, related_name='zip_codes'
    )
    images = models.TextField(blank=True, null=True)
    html = models.TextField(blank=True, null=True)
    css = models.TextField(blank=True, null=True)
    head = models.TextField(blank=True, null=True)
    header = models.TextField(blank=True, null=True)
    footer = models.TextField(blank=True, null=True)
    complete_html = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        return f'{self.id} - {self.name}'


class Template(models.Model):
    """A page template with head, header, footer, and CSS."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    head = models.TextField(blank=True, null=True)
    header = models.TextField(blank=True, null=True)
    footer = models.TextField(blank=True, null=True)
    css = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        return f'{self.id} - {self.name}'


class Section(models.Model):
    """A reusable content section."""

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return f'{self.id} - {self.name}'


class TemplateSection(models.Model):
    """Association between a template and a section with ordering."""

    template = models.ForeignKey(Template, on_delete=models.CASCADE, related_name='template')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='section')
    order = models.PositiveIntegerField()
    default_content = models.TextField(blank=True, null=True)
    ai_response_sample = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('template', 'section')
        verbose_name_plural = 'Template Sections'

    def __str__(self) -> str:
        return f'Template {self.template.id} - Section {self.section.name}'


class AIGeneratedContent(models.Model):
    """AI-generated content for a specific template section and page."""

    template_section = models.ForeignKey(
        TemplateSection, on_delete=models.CASCADE, related_name='ai_generated_contents'
    )
    prompt = models.TextField(blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='pages')

    class Meta:
        verbose_name_plural = 'AI Generated Content'

    def __str__(self) -> str:
        return f'{self.template_section.template.name} - {self.template_section.section.name}'


class UploadedFile(models.Model):
    """An uploaded Excel file for bulk page creation."""

    file = models.FileField(upload_to='', blank=False, null=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, blank=False, null=False, related_name='files'
    )
    temperature = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    class Meta:
        verbose_name_plural = 'Uploaded Files'

    def __str__(self) -> str:
        return f'{self.file} file uploaded at {self.uploaded_at}'


class RegeneratedImage(models.Model):
    """An image regenerated by AI for a project."""

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='regenerated_images', blank=True, null=True
    )
    image = models.ImageField(upload_to='regenerated_images/')
    prompt = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)