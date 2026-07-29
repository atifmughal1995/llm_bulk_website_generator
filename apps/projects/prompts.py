from django.conf import settings

INITIAL_PROMPT_STRUCTURE = """
--------EXAMPLE STARTS--------

  > PROMPT: This is the data I provide:

  Company Name: Rice HVAC
  Service: Ductless Mini-Split Air Conditioner Services
  Service Short form: Ductless AC
  Place: Aurora, CO Colorado 80013

  > PROMPT: And this is the webpage template I have with sections: Map, Heading, Introduction, Why Choose us?, Our Services, How can we help?, Customer Testimonials, Call us and Ending.

  {{
    "Map": "<section id='map'><h2>Find Us in Aurora, CO</h2><iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2890.7976582281396!2d-104.78925272626326!3d39.73931200809025!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x876c7fe0cd2788e9%3A0x64cf74272b7fbd5f!2sAurora%2C%20CO%2080013%2C%20USA!5e0!3m2!1sen!2sin!4v1643056905139!5m2!1en!2sin' width='100%' height='400' style='border:0;' allowfullscreen='' loading='lazy'></iframe></section>",
    "Heading": "<section id='heading'><h1>Ductless AC in Aurora, CO Colorado 80013</h1></section>",
    "Introduction": "<section id='introduction'><h2>Introduction</h2><p>Exceptional Ductless Mini-Split Air Conditioner Services in Aurora, CO</p><p>When it comes to reliable, efficient, and professional ductless mini-split air conditioner services, Rice HVAC stands out as the trusted choice in Aurora, Colorado. Whether you're upgrading your home cooling system, needing maintenance, or planning a new installation, our team is here to provide the expertise and quality you deserve.</p></section>",
    "Why Choose us?": "<section id='why-choose-us'><h2>Why Choose Ductless Mini-Split Air Conditioners?</h2><p>Ductless mini-split systems are a modern solution for cooling and heating your home in Aurora. Here's why they're an excellent choice for Colorado homeowners:</p><ul><li>Energy Efficiency: Unlike traditional systems, ductless mini-splits consume less energy, reducing your utility bills.</li><li>Easy Installation: No bulky ductwork needed, which is perfect for older homes or unique layouts in 80013.</li><li>Affordable pricing and transparent estimates</li><li>Zone Comfort: Customize the temperature in different rooms or zones of your house.</li><li>Eco-Friendly Options: Many models align with eco-friendly standards, ensuring your home is energy-efficient in CO.</li></ul></section>",
    "Our Services": "<section id='our-services'><h2>Our Comprehensive Services</h2><p>At Rice HVAC, we're proud to offer a full range of services tailored to meet your specific needs:</p><ol><li> <h3>Ductless Mini-Split Installation</h3> <p>Looking for a cooling solution tailored to your home or office in Aurora? Our team specializes in professional installations, ensuring your new system is set up for optimal performance.</p></li><li> <h3>Maintenance and Tune-Ups</h3> <p>Regular maintenance can extend the lifespan of your mini-split system. We offer affordable tune-up packages in Colorado to keep your system running smoothly, avoiding costly repairs.</p></li><li> <h3>Repair Services</h3> <p>Experiencing issues with your system in Aurora? Our technicians are highly trained to diagnose and resolve problems quickly, minimizing downtime and discomfort.</p></li><li> <h3>Upgrades and Replacements</h3> <p>Outdated system? Let us help you choose a modern mini-split that enhances comfort and efficiency for your home in 80013.</p></li></ol></section>",
    "How can we help?": "<section id='how-can-we-help'><h2>How Rice HVAC Can Help You in Aurora, CO</h2><p> At Rice HVAC, we don't just provide services—we create solutions. Here's how we help homeowners like you in Aurora:</p><ul><li>Expert Guidance: Our knowledgeable team helps you select the best system for your home and budget.</li><li>Fast Response Times: We value your time and aim to address your HVAC needs promptly in Colorado.</li><li>Transparent Pricing: No hidden fees—just honest, upfront quotes.</li><li>Zone Comfort: Customize the temperature in different rooms or zones of your house.</li><li>Customer-Centric Approach: Your satisfaction is our priority. From consultation to completion, we ensure your experience is seamless.</li></ul></section>",
    "Customer": "<section id='testimonials'><h2>Customer Testimonials</h2><blockquote><p>Rice HVAC did an amazing job installing my ductless mini-split system in Aurora. Their team was professional, and the process was hassle-free. I highly recommend them for anyone in Colorado!</p><footer>- [Satisfied Customer, Aurora, CO]</footer></blockquote><blockquote><p>Quick response time and fantastic service.</p><footer>- [Satisfied Customer, Aurora, CO]</footer></blockquote></section>",
    "Call Us": "<section id='call-us'><h2>Call Us Today to Schedule Your Service</h2><p>Ready to upgrade your comfort with a ductless mini-split air conditioner? Rice HVAC is your go-to solution in Aurora, Colorado. Call us now at <a href='tel:+1234567890'>+1 234 567 890</a> or email us at <a href='mailto:info@example.com'>info@example.com</a>.</p><p>For more insights on energy-efficient cooling solutions, check out this Energy Star Guide for Home Cooling.</p></section>",
    "Ending": "<section id='ending'><h2>Rice HVAC: Where Comfort Meets Innovation</h2><p>Transform your home comfort today in Aurora, Colorado—call us at +1 234 567 890</p><p>Copyright © 2025 Rice HVAC - Ductless Mini-Split Air Conditioners | Powered by Rice HVAC - Ductless Mini-Split Air Conditioners</p></section>"
  }}
--------EXAMPLE ENDS--------

> Can you create a same template for this

Company Name: {company_name}
Service: {service_type}
Place: {target_region}
Zip Code: {zip_code}
Create a webpage having these sections: {sections}

Return JSON data having keys and HTML against them having the structure same as provided. Ensure that the section names match the keys provided and the content should be as rich and longer as given
in the first example. The example is just for the context, no need to use the same content.
"""


REWRITE_PROMPT = """
"{text}"

{prompt}

Ensure the response is in HTML and the structure of HTML is same as provided.
"""


DUMMY_DATA = """
{
  "Map": "<section id='map'><h2>Find Us in Los Angeles, CA</h2><iframe src='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3302.118766523938!2d-118.45135798478353!3d33.99241908063066!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x80c2b94a0d7d27e5%3A0x3b0b6a4e14f8b7b0!2sLos%20Angeles%2C%20CA%2090291%2C%20USA!5e0!3m2!1sen!2sin!4v1643056905139!5m2!1en!2sin' width='100%' height='400' style='border:0;' allowfullscreen='' loading='lazy'></iframe></section>",
  "Heading": "<section id='heading'><h1>Gaming Arcade in Los Angeles, CA 90291</h1></section>",
  "Introduction": "<section id='introduction'><h2>Introduction</h2><p>Immerse yourself in the ultimate gaming experience at our Gaming Arcade in Los Angeles, California. With state-of-the-art equipment and a wide range of games, we provide a haven for gamers of all ages to enjoy.</p><p>Step into a world where excitement knows no bounds and let our arcade be your go-to destination for fun and entertainment.</p></section>",
  "Why Choose Us?": "<section id='why-choose-us'><h2>Why Choose Our Gaming Arcade?</h2><p>Our Gaming Arcade in Los Angeles offers a unique gaming experience that sets us apart from the rest. Here are a few reasons why you should choose us:</p><ul><li>Wide Selection of Games: From classic favorites to the latest releases, we have something for every type of gamer.</li><li>State-of-the-Art Equipment: Enjoy top-of-the-line gaming equipment that enhances your gaming experience.</li><li>Comfortable Environment: Our arcade provides a comfortable and welcoming space for you to relax and enjoy your gaming session.</li><li>Competitive Pricing: We offer affordable rates for hours of entertainment and fun.</li><li>Expert Staff: Our knowledgeable staff is always on hand to assist you and ensure you have a great time.</li></ul></section>",
  "Our Services": "<section id='our-services'><h2>Our Services</h2><p>At our Gaming Arcade in Los Angeles, we offer a range of services to cater to all your gaming needs:</p><ol><li><h3>Gaming Stations</h3><p>Experience gaming like never before with our high-quality gaming stations equipped with the latest technology.</p></li><li><h3>Multiplayer Gaming</h3><p>Challenge your friends or meet new opponents with our multiplayer gaming options that guarantee hours of fun.</p></li><li><h3>Virtual Reality Gaming</h3><p>Dive into a virtual world with our VR gaming experiences that transport you to new and exciting realms.</p></li><li><h3>Gaming Tournaments</h3><p>Compete against other gamers in thrilling tournaments and showcase your skills for a chance to win prizes.</p></li></ol></section>",
  "How can we help?": "<section id='how-can-we-help'><h2>How Our Gaming Arcade Can Help You</h2><p>At our Gaming Arcade in Los Angeles, we are dedicated to providing you with an unforgettable gaming experience. Here's how we can help:</p><ul><li>Personalized Recommendations: Our staff can recommend games based on your preferences and skill level.</li><li>Special Events: Stay updated on our upcoming events and special gaming nights for added excitement.</li><li>Clean and Safe Environment: We prioritize cleanliness and safety to ensure a worry-free gaming experience.</li><li>Community Engagement: Connect with fellow gamers and build lasting friendships in our vibrant gaming community.</li><li>Customer Satisfaction: Your satisfaction is our priority, and we strive to exceed your expectations with every visit.</li></ul></section>",
  "Customer Testimonials": "<section id='testimonials'><h2>Customer Testimonials</h2><blockquote><p>The Gaming Arcade in Los Angeles is my go-to spot for an amazing gaming experience. The variety of games and friendly staff always make my visits enjoyable.</p><footer>- [Happy Gamer, Los Angeles, CA]</footer></blockquote><blockquote><p>I love the competitive atmosphere at this arcade. The gaming tournaments are intense, and the prizes are worth it!</p><footer>- [Dedicated Gamer, Los Angeles, CA]</footer></blockquote></section>",
  "Call us": "<section id='call-us'><h2>Call Us Today to Level Up Your Gaming Experience</h2><p>Ready to elevate your gaming experience in Los Angeles? Visit our Gaming Arcade today and immerse yourself in a world of fun and excitement. Call us now at <a href='tel:+1234567890'>+1 234 567 890</a> or email us at <a href='mailto:info@example.com'>info@example.com</a>.</p><p>For updates on upcoming tournaments and events, follow us on social media.</p></section>",
  "Ending": "<section id='ending'><h2>Experience Unmatched Gaming Thrills in Los Angeles</h2><p>Visit our Gaming Arcade in Los Angeles, CA 90291, and discover a world of gaming excitement like never before.</p><p>Copyright © 2025 Gaming Arcade - Where Fun Knows No Limits | Powered by Gaming Arcade - Where Fun Knows No Limits</p></section>"
}
"""


HOMEPAGE_PROMPT = """
> Data I provide:
Service: Air Conditioners
Sections: Banner, About Us, Services, How It Works


> Response:
{{
    "Banner": {{
        "h1": "Year-round comfort and Efficiency with Ductless Mini-Split Air Conditioners",
        "content": "Efficient, quiet, and easy to install—perfect temperature control for any room, without the need for ducts."
    }},
    "Services": {{
        "h1": "Ductless Mini-Split Air Conditioners Services For Every Season",
        "content": "At Rice HVAC, we provide a range of air conditioning services to keep your home comfortable year-round. Our expert team delivers quality solutions tailored to your needs, from installation to maintenance.",
        "data": [
            {{
                "h1": "Air Conditioner Installation",
                "content": "We ensure your air conditioning system is installed correctly for optimal performance and reliable comfort.",
            }},
            {{
                "h1": "Air Conditioner Repair",
                "content": "Our skilled technicians quickly diagnose and repair any issues with your AC system, restoring comfort promptly and effectively.",
            }},
            {{
                "h1": "Routine Maintenance",
                "content": "Regular maintenance services, including inspections and cleaning, keep your AC running efficiently and extend its lifespan.",
            }},
            {{
                "h1": "Consultation",
                "content": "We begin with a thorough consultation to understand your specific needs and assess your space. This allows us to recommend the best solutions tailored to your requirements."
            }}
        ]
    }},
    "About": {{
        "h1": "Ductless Mini-Split Air Conditioners Experts You Can Trust",
        "content": "Our team of trusted experts specializes in ductless mini-split air conditioner installation and repair, ensuring top-notch service and dependable results. With years of experience, we're committed to providing personalized solutions that deliver comfort, energy efficiency, and peace of mind."
    }},
    "How It Works": {{
        "h1": "How It Works",
        "content": "Our process begins with a personalized consultation to assess needs, followed by a comprehensive evaluation of your space. Our skilled team then executes professional installation or repair services, ensuring quality and efficiency.",
        "data": [
            {{
                "h1": "Air Conditioner Installation",
                "content": "We ensure your air conditioning system is installed correctly for optimal performance and reliable comfort.",
            }},
            {{
                "h1": "Air Conditioner Repair",
                "content": "Our skilled technicians quickly diagnose and repair any issues with your AC system, restoring comfort promptly and effectively.",
            }},
            {{
                "h1": "Routine Maintenance",
                "content": "Regular maintenance services, including inspections and cleaning, keep your AC running efficiently and extend its lifespan.",
            }},
            {{
                "h1": "Consultation",
                "content": "We begin with a thorough consultation to understand your specific needs and assess your space. This allows us to recommend the best solutions tailored to your requirements."
            }}
        ]
    }},
    "We're Here for You": {{
        "h1": "We're Here for You",
        "content": "Need help with a plumbing issue? We offer:",
        "data": [
            {{
                "h1": "Air Conditioner Installation",
                "content": "We ensure your air conditioning system is installed correctly for optimal performance and reliable comfort.",
            }},
            {{
                "h1": "Air Conditioner Repair",
                "content": "Our skilled technicians quickly diagnose and repair any issues with your AC system, restoring comfort promptly and effectively.",
            }},
            {{
                "h1": "Routine Maintenance",
                "content": "Regular maintenance services, including inspections and cleaning, keep your AC running efficiently and extend its lifespan.",
            }},
            {{
                "h1": "Consultation",
                "content": "We begin with a thorough consultation to understand your specific needs and assess your space. This allows us to recommend the best solutions tailored to your requirements."
            }}
        ]
    }},
    "Get a Free Estimate Today": {{
        "h1": "Get a Free Estimate Today!",
        "content": "Call now to schedule an inspection and receive a quote for your plumbing needs."
    }},
    "Who are we": {{
        "h1": "We're Here for You",
        "content": "Need help with a plumbing issue? We offer:",
        "data": [
            {{
                "h1": "Air Conditioner Installation",
                "content": "We ensure your air conditioning system is installed correctly for optimal performance and reliable comfort.",
            }},
            {{
                "h1": "Air Conditioner Repair",
                "content": "Our skilled technicians quickly diagnose and repair any issues with your AC system, restoring comfort promptly and effectively.",
            }},
            {{
                "h1": "Routine Maintenance",
                "content": "Regular maintenance services, including inspections and cleaning, keep your AC running efficiently and extend its lifespan.",
            }},
            {{
                "h1": "Consultation",
                "content": "We begin with a thorough consultation to understand your specific needs and assess your space. This allows us to recommend the best solutions tailored to your requirements."
            }}
        ]
    }},
}}


> Give me a reponse in the same format provided above against the following input:
Service: {service_type}
Sections: {sections}

Return JSON data having keys. Ensure that the keys are same as provided in Sections field.

Don't add ```json ```
"data" key in "Services" should be a list of four like in the example.
"data" key in "How It Works" should be a list of four like in the example.
"data" key in "We're Here for You" should be a list of four like in the example.
"data" key in "Who are we" should be a list of four like in the example.
"""


HOMEPAGE_PROMPT = """
You are an expert web developer and UI/UX designer specializing in creating engaging homepages.

Task: Create a professional homepage for a {service_type} business that incorporates all the specified sections.

Required Sections:
{sections}

Required Components:
    1. index.html
        - Includes the full HTML document with <html>, <head>, and <body> tags.
        - Inside <head>
            - Add all global settings (fonts, font color, base styles, responsive meta tags).
            - Include global CSS styles for theme, layout, sections background color and typography directly within a <style> tag.
        - Inside <body>
            - Add a <header id="header">
                - Use class="nav-links" for header
                - A "Home" link at the start redirecting to {homepage_link}
                - A "Service Area" link at the end redirecting to {service_area_link}
                - Other links to content sections
            - Add an empty <div id="content-container"> with "||CONTENT||" placeholder between the header and footer
            - Add a <footer id="footer">
                - Social media links
                - Contact information
                - Copyright notice

    2. content.html
        - Contains all the actual content based.
        - Page-specific styles and scripts should be written directly inside this file using <style> and <script> tags (no imports).

    3. services.html {create_service_page_flag}
        - Contains multiple HTML blocks, each representing one service.
        - Each block should include:
            - The service name
            - A suggested URL-friendly slug (e.g., `/service-name`)
            - Design it like a standalone section/page so it can be reused as an independent service page.
            - Use this link {service_detail_page_link}/<slug>/ for redirection
            - Add <head></head> at the top having SEO optimized meta tags
        - Wrap each service block in a comment that clearly separates it like <!-- Service: Service Name -->...<!-- /slug -->.

Design Guidelines:
    - Review the GrapeJS documentation for any specific requirements for HTML structures
    - Ensure that CSS and JavaScript are properly linked and compatible with GrapeJS
    - Test the final output within the GrapeJS editor to confirm functionality
    - Use a color scheme appropriate for {service_type} industry
    - Create a responsive header optimized for mobile screens. Use a hamburger icon without any CSS classes. Do not create a separate mobile navigation; instead, implement a script to hide and show the header when the hamburger icon is clicked. Ensure the design is simple and user-friendly
    - The script should toggle the visibility of the mobile header when a button is clicked.
    - Ensure that the script is compatible with GrapeJS's component structure and lifecycle.
    - Include comments in the code for clarity and maintainability.
    - If there's a form on the webpage, ensure its id attribute is set to "contact-form-cpp"
    - If there's a form on the webpage, don't add any form submission handler
    - If there's a form on the webpage, add Google reCAPTCHA v2 to the form and use "my-site-id"
    - Use Tailwind CSS framework and make sure to use all the pre-defined classes
    - Maintain consistent spacing and typography
    - Include modern UI elements and intuitive navigation
    - Use semantic HTML5 structure
    - Ensure responsive design principles
    - Include appropriate calls-to-action
    - Optimize for best user experience across devices
    - Add full-width hero section with a background image and a strong headline
    - Ensure proper semantic HTML structure
    - Incorporate responsive design principles
    - Don't add svg or similar long html tags
    - Ensure all images load correctly
    - Check for any image links that result in a 404 error or similar broken link
    - Review each section of the webpage to confirm that the images used are contextually appropriate and enhance the content
    - Add SEO optimized meta & title and tags in the <head>
    - Please replace the contact phone number in the text with the placeholder ||CONTACT_PHONE_NO||. Make sure to use this exact placeholder and ensure that no actual phone number is included in the final output
    
Additional Guidelines (Take Priority Over Others):
    - {additional_guideline}

Please provide output in the following order:
    IMPORTANT - Both code blocks start and end with ```html and ```
        - First: index.html
        - Second: content.html
        - Third: services.html {create_service_page_flag}
"""


GENERATE_SERVICE_PAGE_PROMPT = """
> Data I provide:
Service: Air Conditioners
Sections: Banner, About Us, Services, How It Works


> Response:
{{
    {sample_section_data}
}}


> Give me a reponse in the same format provided above against the following input:
Service: {service_type}
Sections: {sections}

Return JSON data having keys. Ensure that the keys are same as provided in Sections field.
Don't add ```json ```
"""


GENERATE_SERVICE_PAGE_PROMPT  = """
--------EXAMPLE STARTS--------

  > PROMPT: This is the data I provide:

  Company Name: Rice HVAC
  Service: Ductless Mini-Split Air Conditioner Services
  Service Short form: Ductless AC
  Place: Aurora, CO Colorado 80013

  > PROMPT: And this is the webpage template I have with sections: Map, Heading, Introduction, Why Choose us?, Our Services, How can we help?, Customer Testimonials, Call us and Ending.

  {{
      {sample_section_data}
  }}
--------EXAMPLE ENDS--------

> Can you create a same template for this

Company Name: {company_name}
Service: {service_type}
Place: {target_region}
Zip Code: {zip_code}
Create a webpage having these sections: {sections}

Return JSON data having keys and HTML against them having the structure same as provided. Ensure that the section names match the keys provided and the content should be as rich and longer as given
in the first example. The example is just for the context, no need to use the same content.

Don't add ```json ```
"""


REWRITE_SECTION_PROMPT = """
{object}

Update the values of this JSON object according to the following prompt:
{prompt}

Ensure the response is exactly in the same format as provided and no need to add any new key.
Do not add apostrophe (') anywhere in the value.
Use <br/> instead of newline or "\\n"
Don't add ```json ```
"""

CITY_PAGE_PROMPT = """
You are an expert web developer and UI/UX designer specializing in creating engaging service pages. 

Task: Create a professional webpage for a {service_type} business that incorporates all the specified sections and location.

Required Sections: {sections}
Location: {target_region}
Company Name: {company_name}


Required Components:
    1. head.html
        - Create a <head></head> having SEO optimized meta tags related to the content. Ensure it is in a separate HTML code block.
    2. content.html
        - Use the provided base HTML: {base_html}
        - Do not modify any part of the base HTML except for the <div></div> that contains the text ||CONTENT||
        - All content, styles (<style>), and scripts (<script>) must be placed only inside this ||CONTENT|| <div>
        - The <head> and any other parts of the base HTML must remain unchanged

Design Guidelines:
    - A complete HTML and CSS code structure for a responsive service page
    - If there's a form on the webpage, ensure its id attribute is set to "contact-form-cpp"
    - If there's a form on the webpage, don't add any form submission handler
    - If there's a form on the webpage, add Google reCAPTCHA v2 to the form and use "my-site-id"
    - Use Tailwind CSS framework and make sure to use all the pre-defined classes
    - The design should align with industry standards for {service_type} businesses
    - Include modern UI elements and intuitive navigation
    - Ensure proper semantic HTML structure
    - Incorporate responsive design principles
    - Create a full-width hero section for a webpage. The hero section should have a background image. Inside this section, divide the content into two columns. In the left column, add a strong headline that captures attention. In the right column, insert a Google Map using an <iframe> tag to display a specific location. Make sure the layout is visually appealing and the elements are well-aligned
    - Make sure the header and footer are same as provided, there must be no change in them
    - Use a color scheme appropriate for {service_type} industry
    - Maintain consistent spacing and typography
    - Include appropriate calls-to-action
    - Ensure optimal user experience across devices
    - Don't add svg or similar long html tags
    - Please replace the contact phone number in the text with the placeholder ||CONTACT_PHONE_NO||. Make sure to use this exact placeholder and ensure that no actual phone number is included in the final output

Follow the guidelines mentioned below. If they conflict with any previously stated guidelines, the following ones take precedence:
Additional Guidelines:
    - {additional_guideline}

Please structure your response with:
    IMPORTANT: Both code blocks start and end with ```html and ```
    - head.html
    - content.html (which I will inject in the base.html in the end myself)
"""


NO_CONTENT_SECTION_HTML = "<section style='padding: 5%; min-height: 70vh;'> No content available. </section>"

DEFAULT_HOMEPAGE_SECTIONS = ['Banner', 'About Us', 'Services', 'How It Works']
DEFAULT_SERVICE_PAGE_SECTIONS = ['Map', 'Introduction', 'Why Choose Us?', 'Our Services', 'How can we help?', 'Customer', 'Call us', 'Ending']


REGENERATION_PROMPT = """
I want you to act as a web developer and update the given HTML by using this command: {prompt}

Important notes:
    1. Return ONLY the complete updated HTML with no explanations.
    2. Ensure that no HTML tags are removed and the structure remains unchanged.
    3. Don't remove any div or another tag having no content in it.
    2. Don't add ```html ```
    4. Make precise changes exactly as specified.
    5. Add all the global settings in the <head> tag i.e font and font color
    6. Do not modify the <div></div> that contains the text ||CONTENT||

The current HTML structure is as follows: {html}
"""

NGINX_TEMPLATE = """
server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://127.0.0.1:8000/project/{project_id}/homepage/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }}

    location /static/ {{
        proxy_pass http://127.0.0.1:8000/static/;
    }}

    location /media/ {{
        proxy_pass http://127.0.0.1:8000/media/;
    }}

    location /styles.css {{
        proxy_pass http://127.0.0.1:8000/project/{project_id}/style.css;
    }}
}}
"""

JAVASCRIPT_REDIRECTING_SNIPPET = f"""
<script>
document.addEventListener("DOMContentLoaded", function() {{
    if (!window.location.href.includes("{settings.BACKEND_IP}") && !window.location.href.includes("127.0.0.1")) {{
        const links = document.querySelectorAll("a[href]");
        links.forEach(link => {{
            link.href = link.href.replace(/\\/project\\/\\d+\\//, "/");
        }});
    }}
}});
</script>
"""

EMAILJS_CODE_SNIPPET = """
<script src="https://cdn.jsdelivr.net/npm/emailjs-com@3/dist/email.min.js"></script>
<script>
  (function() {{
    emailjs.init("{public_key}"); // Replace with your public key
  }})();
</script>

<script>
  document.getElementById("contact-form-cpp").addEventListener("submit", function(e) {{
    e.preventDefault();

    const form = this;
    const formData = new FormData(form);
    let combinedMessage = "";
    let captchaValue = "";

    for (const [key, value] of formData.entries()) {{
      if (key.toLowerCase().includes("captcha")) {{
        captchaValue = value.trim();
        continue;
      }}
      combinedMessage += `${{key}}: ${{value}}\\n`;
    }}

    // Empty captcha check
    if (!captchaValue) {{
      alert("Please verify you're human.");
      return;
    }}

    // Prepare data object with a single field
    const templateParams = {{
      message: combinedMessage,
      to_email: '{to_email}'
    }};

    emailjs.send("{service_id}", "{template_id}", templateParams)
      .then(() => {{
        alert("Message sent successfully!");
        form.reset();
      }}, (error) => {{
        console.error("FAILED...", error);
        alert("Oops! Something went wrong.");
      }});
  }});
</script>
"""

PROJECT_PAGE_PROMPT = """
You are an expert web developer and UI/UX designer specializing in creating engaging service pages. 

Task: Create a professional webpage for a {service_type} business that incorporates all the specified sections and location.

Page Name: {page_name}
Company Name: {company_name}

Required Components:
    1. content.html
        - Use the provided base HTML: {base_html}
        - Do not modify any part of the base HTML except for the <div></div> that contains the text ||CONTENT||
        - All content, styles (<style>), and scripts (<script>) must be placed only inside this ||CONTENT|| <div>
        - The <head> and any other parts of the base HTML must remain unchanged

    2. base.html
        - Add a link "{page_name}"  redirecting to this "{page_link}" in header and footer.

Design Guidelines:
    - A complete HTML and CSS code structure for a responsive service page
    - If there's a form on the webpage, ensure its id attribute is set to "contact-form-cpp"
    - If there's a form on the webpage, don't add any form submission handler
    - If there's a form on the webpage, add Google reCAPTCHA v2 to the form and use "my-site-id"
    - Use Tailwind CSS framework and make sure to use all the pre-defined classes
    - The design should align with industry standards for {service_type} businesses
    - Include modern UI elements and intuitive navigation
    - Ensure proper semantic HTML structure
    - Incorporate responsive design principles
    - Make sure the header and footer are same as provided, there must be no change in them
    - Use a color scheme appropriate for {service_type} industry
    - Maintain consistent spacing and typography
    - Include appropriate calls-to-action
    - Ensure optimal user experience across devices
    - Don't add svg or similar long html tags

Follow the guidelines mentioned below. If they conflict with any previously stated guidelines, the following ones take precedence:
Additional Guidelines:
    - {additional_guideline}

Please structure your response with:
    IMPORTANT: Both code blocks start and end with ```html and ```
    - First: content.html (which I will inject in the base.html in the end myself)
    - Second: base.html (updated base html)
"""