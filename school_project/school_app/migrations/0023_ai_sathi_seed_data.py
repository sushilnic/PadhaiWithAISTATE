"""
Data migration: seeds AISathiClass, AISathiSubject, AISathiChapter tables
with the NCERT curriculum data that was previously hardcoded in the template.
"""
from django.db import migrations

CURRICULUM = {
    6: {
        "Math": [
            "Knowing Our Numbers", "Whole Numbers", "Playing with Numbers",
            "Basic Geometrical Ideas", "Understanding Elementary Shapes", "Integers",
            "Fractions", "Decimals", "Data Handling", "Mensuration",
            "Algebra", "Ratio and Proportion", "Symmetry", "Practical Geometry",
        ],
        "Science": [
            "Food: Where Does It Come From?", "Components of Food", "Fibre to Fabric",
            "Sorting Materials into Groups", "Separation of Substances", "Changes Around Us",
            "Getting to Know Plants", "Body Movements",
            "The Living Organisms and Their Surroundings",
            "Motion and Measurement of Distances", "Light, Shadows and Reflections",
            "Electricity and Circuits", "Fun with Magnets",
        ],
        "English": [
            "Who Did Patrick's Homework", "How the Dog Found Himself", "Taro's Reward",
            "An Indian-American Woman in Space", "A Different Kind of School", "Who I Am",
            "Fair Play", "A Game of Chance", "Desert Animals", "The Banyan Tree",
        ],
        "Hindi": [
            "वह चिड़िया जो", "बचपन", "नादान दोस्त", "चाँद से थोड़ी-सी गप्पें",
            "अक्षरों का महत्व", "पार नज़र के", "साथी हाथ बढ़ाना", "मैं हूँ",
            "किताब से दोस्ती",
        ],
        "Social Science": [
            "History: What, Where, How and When",
            "From Hunting-Gathering to Growing Food", "In the Earliest Cities",
            "What Books and Burials Tell Us", "Kingdoms, Kings and an Early Republic",
            "Understanding Chakravartin",
            "Geography: The Earth in the Solar System",
            "Globe: Latitudes and Longitudes", "Maps",
            "Civics: Understanding Diversity", "Diversity and Discrimination",
            "What is Government", "Key Elements of Democratic Institutions",
        ],
    },
    7: {
        "Math": [
            "Integers", "Fractions and Decimals", "Data Handling", "Simple Equations",
            "Lines and Angles", "The Triangle and Its Properties",
            "Congruence of Triangles", "Comparing Quantities", "Rational Numbers",
            "Practical Geometry", "Perimeter and Area", "Algebraic Expressions",
            "Exponents and Powers", "Symmetry", "Visualising Solid Shapes",
        ],
        "Science": [
            "Nutrition in Plants", "Nutrition in Animals", "Fibre to Fabric", "Heat",
            "Acids, Bases and Salts", "Physical and Chemical Changes",
            "Respiration in Organisms", "Transportation in Animals and Plants",
            "Reproduction in Plants", "Motion and Time",
            "Electric Current and Its Effects", "Light",
            "Forests: Our Lifeline", "Wastewater Story",
        ],
        "English": [
            "Three Questions", "A Gift of Chappals", "Gopal and the Hilsa Fish",
            "The Ashes That Made Trees Bloom", "Quality", "Expert Detectives",
            "The Invention of Vita-Wonk", "Keeping It from Harold", "Chivvy", "The Rebel",
        ],
        "Hindi": [
            "हम पंछी उन्मुक्त गगन के", "दादी माँ", "हिमालय की बेटियाँ", "कंचा",
            "मीठाईवाला", "रक्त और हमारा शरीर", "पापा खो गए", "साखी", "वाख", "ऋतुराज",
        ],
        "Social Science": [
            "Tracing Changes Through a Thousand Years", "New Kings and Kingdoms",
            "The Delhi Sultanate", "The Mughal Empire", "Rulers and Buildings",
            "Town, Bazaar and Trade",
            "Environment", "Inside Our Earth", "Our Changing Earth",
            "On Equality", "Role of the Government in Health",
            "How the State Government Works", "Understanding Media",
        ],
    },
    8: {
        "Math": [
            "Rational Numbers", "Linear Equations in One Variable",
            "Understanding Quadrilaterals", "Practical Geometry", "Data Handling",
            "Squares and Square Roots", "Cubes and Cube Roots", "Comparing Quantities",
            "Algebraic Expressions and Identities", "Visualising Solid Shapes",
            "Mensuration", "Exponents and Powers", "Direct and Inverse Proportions",
            "Factorisation", "Introduction to Graphs", "Playing with Numbers",
        ],
        "Science": [
            "Crop Production and Management", "Microorganisms: Friend and Foe",
            "Synthetic Fibres and Plastics", "Materials: Metals and Non-Metals",
            "Coal and Petroleum", "Combustion and Flame",
            "Cell – Structure and Functions", "Reproduction in Animals",
            "Reaching the Age of Adolescence", "Force and Pressure", "Friction",
            "Sound", "Chemical Effects of Electric Current",
            "Some Natural Phenomena", "Conservation of Plants and Animals",
        ],
        "English": [
            "The Best Christmas Present", "The Tsunami", "Glimpses of the Past",
            "Bepin Choudhury's Lapse of Memory", "The Summit Within",
            "The School Play", "Reaching for the Stars", "Jalebis", "Black Aeroplane",
        ],
        "Hindi": [
            "ध्वनि", "लाख की चूड़ियाँ", "बस की यात्रा", "दीवानों की हस्ती",
            "चिट्ठियों की अनूठी दुनिया", "भगवान के डाकिये",
            "क्या निराश हुआ जाए", "यह दीप अकेला", "कबीरवाणी", "संसार",
        ],
        "Social Science": [
            "How, When and Where", "The British Took Control", "Ruling the Roost",
            "India After Independence", "Understanding the Secular State",
            "Resources", "Agriculture", "Minerals and Power Resources",
            "The Indian Constitution", "Understanding Secularism",
            "Vivekananda: His Four Yogas", "Bhagat Singh: Courage and Sacrifice",
        ],
        "Computer Science": [
            "Introduction to Computers", "Introduction to Python Programming",
            "Python Programming - Data Types and Variables", "Operators and Expressions",
            "Control Structures - Conditional Statements", "Control Structures - Loops",
            "Functions", "Lists and Strings", "Dictionaries and Sets", "File Handling",
        ],
        "Physical Education": [
            "Physical Fitness and Wellness", "Sports and Games Rules",
            "Yoga and its Benefits", "First Aid and Safety", "Sports Nutrition",
            "Movement and Posture", "Athletic Skills", "Team Sports Fundamentals",
            "Individual Sports Fundamentals", "Healthy Lifestyle",
        ],
    },
    9: {
        "Math": [
            "Number Systems", "Polynomials", "Coordinate Geometry",
            "Linear Equations in Two Variables", "Introduction to Euclid's Geometry",
            "Lines and Angles", "Triangles", "Quadrilaterals",
            "Areas of Parallelograms and Triangles", "Circles", "Constructions",
            "Heron's Formula", "Surface Areas and Volumes", "Statistics", "Probability",
        ],
        "Science": [
            "Matter in Our Surroundings", "Is Matter Around Us Pure",
            "Atoms and Molecules", "Structure of the Atom",
            "The Fundamental Unit of Life", "Tissues",
            "Diversity in Living Organisms", "Why Do We Fall Ill",
            "Natural Resources", "Improvement in Food Resources",
            "Motion", "Force and Laws of Motion", "Gravitation",
            "Work and Energy", "Sound",
        ],
        "English": [
            "The Fun They Had", "The Sound of Music", "The Little Girl",
            "A Truly Beautiful Mind", "My Childhood", "Packing",
            "Reach for the Top", "The Bond of Love", "Katrina", "If I Were You",
        ],
        "Hindi": [
            "दो बैलों की कथा", "ल्हासा की ओर", "उपभोक्तावाद की संस्कृति",
            "साँवले सपनों की याद", "नाना साहब की पुत्री देवी मैना",
            "प्रेमचंद की कहानी उपहार", "मेरे बचपन के दिन", "संस्कृति", "गिरगिट",
            "अग्नि पथ",
        ],
        "Social Science": [
            "The French Revolution", "Socialism in Europe and the Russian Revolution",
            "Nazism and the Rise of Hitler", "India – Size and Location",
            "Physical Features of India", "Drainage", "Climate",
            "Natural Vegetation and Fauna", "Population",
            "What is Democracy", "Constitutional Design", "Electoral Politics",
        ],
        "Computer Science": [
            "Python Programming - Basics", "Python Programming - Control Structures",
            "Functions and Modules", "Data Structures - Lists and Tuples",
            "Data Structures - Dictionaries and Sets", "File Handling",
            "Error Handling and Exceptions", "Object-Oriented Programming Concepts",
            "Database Concepts", "Networking Basics",
        ],
        "Physical Education": [
            "Physical Fitness - Cardiovascular Endurance",
            "Physical Fitness - Muscular Strength", "Physical Fitness - Flexibility",
            "Yoga - Asanas and Benefits", "Sports - Athletics and Games",
            "Sports - Racket Games", "Sports - Aquatic Activities",
            "First Aid in Sports", "Nutrition and Health",
            "Mental Health and Stress Management",
        ],
    },
    10: {
        "Math": [
            "Real Numbers", "Polynomials",
            "Pair of Linear Equations in Two Variables", "Quadratic Equations",
            "Arithmetic Progressions", "Triangles", "Coordinate Geometry",
            "Trigonometry", "Applications of Trigonometry", "Circles",
            "Constructions", "Areas Related to Circles",
            "Surface Areas and Volumes", "Statistics", "Probability",
        ],
        "Science": [
            "Chemical Reactions and Equations", "Acids, Bases and Salts",
            "Metals and Non-Metals", "Carbon and Its Compounds",
            "Life Processes", "Control and Coordination",
            "How Do Organisms Reproduce", "Heredity and Evolution",
            "Light – Reflection and Refraction",
            "The Human Eye and the Colourful World", "Electricity",
            "Magnetic Effects of Electric Current", "Sources of Energy",
            "Our Environment", "Management of Natural Resources",
        ],
        "English": [
            "A Letter to God", "Nelson Mandela: A Long Walk to Freedom",
            "Two Stories About Flying",
            "From a Railway Carriage & The Road Not Taken",
            "A Tiger in the House", "The Midnight Visitor",
            "Bholi", "The Book That Saved My Life", "The Proposal", "The Necklace",
        ],
        "Hindi": [
            "पद", "राम-लक्ष्मण-परशुराम संवाद", "आत्मत्राण",
            "उत्साह और हिमालय", "यमराज का दूत", "छायावाद",
            "छायावाद काव्य संग्रह", "आदमी का मूल्य", "नेताजी का चश्मा",
            "बड़े भाई साहब", "डायरी का एक पन्ना", "ल्हासा की ओर",
        ],
        "Social Science": [
            "The Rise of Nationalism in Europe", "The Indus Valley Civilization",
            "The Vedic Age", "Early Kingdoms", "The Mauryan Empire",
            "The Post Mauryan Period", "The Sultanate Period", "The Mughal Empire",
            "Colonialism", "The British Raj", "The Revolt of 1857",
            "Indian National Movement", "Resources and Development",
            "Forest and Wildlife", "Water Resources", "Mineral and Energy Resources",
            "Agriculture", "Democratic Politics", "Power Sharing Arrangements",
            "Competition Among Political Parties", "Challenges to Democracy",
        ],
        "Computer Science": [
            "Introduction to Algorithm and Flowchart",
            "Fundamentals of Python Programming",
            "Python - Data Types and Variables", "Python - Control Structures",
            "Functions and Parameters", "Strings and String Manipulation",
            "Lists and Tuples", "Dictionaries and Sets",
            "File Handling and Exception Handling",
            "Introduction to Database Management Systems",
        ],
        "Physical Education": [
            "Planning and Organization of Physical Education",
            "Physical Fitness Assessment", "Training Principles and Adaptations",
            "Sports and Games - Rules and Techniques", "Yoga for Health and Wellness",
            "First Aid and Safety Measures", "Health and Nutrition for Athletes",
            "Stress Management and Relaxation", "Performance Appraisal",
            "Life Skills and Character Development",
        ],
    },
    11: {
        "Physics": [
            "Physical World and Measurement", "Kinematics", "Laws of Motion",
            "Work, Energy and Power",
            "Motion of System of Particles and Rigid Body", "Gravitation",
            "Properties of Bulk Matter – Elasticity",
            "Properties of Bulk Matter – Fluid Pressure",
            "Thermal Properties of Matter", "Thermodynamics",
            "Kinetic Theory of Gases", "Oscillations", "Waves",
        ],
        "Chemistry": [
            "Some Basic Concepts of Chemistry", "Structure of Atom",
            "Classification of Elements and Periodicity in Properties",
            "Chemical Bonding and Molecular Structure", "States of Matter",
            "Thermodynamics", "Equilibrium", "Redox Reactions", "Hydrogen",
            "The s-Block Element", "The p-Block Element – Group 13 and 14",
            "Organic Chemistry: Some Basic Principles and Techniques",
            "Hydrocarbons", "Environmental Chemistry",
        ],
        "Biology": [
            "The Living World", "Biological Classification", "Plant Kingdom",
            "Animal Kingdom", "Morphology of Flowering Plants",
            "Anatomy of Flowering Plants", "Structural Organisation in Animals",
            "Cell: The Unit of Life", "Biomolecules", "Cell Cycle and Cell Division",
            "Transport in Plants", "Mineral Nutrition",
            "Photosynthesis in Higher Plants", "Respiration in Plants",
            "Plant Growth and Development",
        ],
        "Math": [
            "Sets", "Relations and Functions", "Trigonometric Functions",
            "Principle of Mathematical Induction",
            "Complex Numbers and Quadratic Equations", "Linear Inequalities",
            "Permutations and Combinations", "Binomial Theorem",
            "Sequences and Series", "Straight Lines", "Conic Sections",
            "Introduction to Three Dimensional Geometry",
            "Limits and Derivatives", "Mathematical Reasoning",
            "Statistics", "Probability",
        ],
        "Accounting": [
            "Introduction to Accounting", "Theory Base of Accounting",
            "Recording of Transactions - I", "Recording of Transactions - II",
            "Bank Reconciliation Statement",
            "Trial Balance and Rectification of Errors",
            "Depreciation, Provisions and Reserves", "Bills of Exchange",
            "Final Accounts - I", "Final Accounts - II", "Final Accounts - III",
            "Accounts of Not-for-Profit Organizations",
            "Partnership Accounts - Fundamentals",
            "Partnership Accounts - Admission of a Partner",
        ],
        "Business Studies": [
            "Nature and Significance of Management", "Principles of Management",
            "Business Environment", "Planning", "Organising", "Staffing",
            "Directing", "Controlling", "Financial Management", "Financial Planning",
            "Working Capital Management", "Marketing Management",
            "Consumer Protection",
        ],
        "Economics": [
            "Introduction to Economics", "Consumer Equilibrium and Demand",
            "Producer Equilibrium and Supply",
            "The Market Forms and Price Determination",
            "National Income Accounting", "Money Supply and Inflation",
            "Banking and Finance", "Government Budget and Fiscal Policy",
            "Balance of Payments", "Aggregate Demand and Supply",
        ],
        "Computer Science": [
            "Computer Organization and Architecture",
            "Boolean Algebra and Logic Gates",
            "Programming in Python - Basics",
            "Programming in Python - Data Structures",
            "Database Management Systems", "Computer Networks",
            "Web Technologies", "Software Engineering", "Cybersecurity",
        ],
        "Informatics Practices": [
            "Introduction to Informatics Practices", "Database Concepts",
            "Structured Query Language - Basics",
            "Structured Query Language - Advanced",
            "Web Applications", "Software Development", "Cloud Computing",
            "Cybersecurity Fundamentals", "Data Analysis and Visualization",
        ],
    },
    12: {
        "Math": [
            "Relations and Functions", "Inverse Trigonometric Functions",
            "Matrices", "Determinants", "Continuity and Differentiability",
            "Applications of Derivatives", "Integrals", "Applications of Integrals",
            "Differential Equations", "Vector Algebra",
            "Three Dimensional Geometry", "Linear Programming", "Probability",
        ],
        "Physics": [
            "Electric Charges and Fields",
            "Electrostatic Potential and Capacitance", "Current Electricity",
            "Moving Charges and Magnetism", "Magnetism and Matter",
            "Electromagnetic Induction", "Alternating Current",
            "Electromagnetic Waves", "Ray Optics and Optical Instruments",
            "Wave Optics", "Dual Nature of Radiation and Matter",
            "Atoms", "Nuclei", "Semiconductor Electronics",
        ],
        "Chemistry": [
            "Solid State", "Solutions", "Electrochemistry", "Chemical Kinetics",
            "Surface Chemistry",
            "General Principles and Processes of Isolation of Elements",
            "The p-Block Elements", "The d- and f-Block Elements",
            "Coordination Compounds", "Haloalkanes and Haloarenes",
            "Alcohols, Phenols and Ethers",
            "Aldehydes, Ketones and Carboxylic Acids", "Amines",
            "Biomolecules", "Polymers", "Chemistry in Everyday Life",
        ],
        "Biology": [
            "Reproduction in Organisms",
            "Sexual Reproduction in Flowering Plants", "Human Reproduction",
            "Reproductive Health", "Principles of Inheritance and Variation",
            "Molecular Basis of Inheritance", "Evolution",
            "Human Health and Disease",
            "Strategies for Enhancement in Food Production",
            "Microbes in Human Welfare",
            "Biotechnology: Principles and Processes",
            "Biotechnology and Its Applications",
            "Organisms and Populations", "Ecosystem",
            "Biodiversity and Conservation", "Environmental Issues",
        ],
        "Accounting": [
            "Accounting for Partnership Firms - Fundamentals",
            "Reconstitution of Partnership - Retirement/Death",
            "Dissolution of Partnership Firm", "Accounting for Share Capital",
            "Accounting for Debentures", "Financial Statements of a Company",
            "Analysis of Financial Statements – I",
            "Analysis of Financial Statements – II",
            "Cash Flow Statement", "Accounting Ratios",
            "Accounts from Incomplete Records",
        ],
        "Business Studies": [
            "Corporate Governance and Business Ethics",
            "Financial Management and Analysis", "Business Administration",
            "Consumer Protection", "Entrepreneurship", "Strategic Management",
            "International Business", "Supply Chain Management",
            "Corporate Responsibility and Sustainability", "Marketing Strategy",
        ],
        "Economics": [
            "Macroeconomics - Introduction", "National Income Accounting",
            "Money and Inflation", "Banking System", "Government Budget",
            "Foreign Exchange and Balance of Payments",
            "Aggregate Demand and Supply",
            "Consumption and Investment Functions",
            "Aggregate Demand and Output", "Monetary Policy and Fiscal Policy",
        ],
        "Computer Science": [
            "Python Programming - Advanced", "Object-Oriented Programming",
            "Data Structures and Algorithms", "Databases and SQL",
            "Web Development", "Cybersecurity and Cryptography",
            "Artificial Intelligence and Machine Learning",
            "Software Engineering Practices", "Cloud Computing and IoT",
        ],
        "Informatics Practices": [
            "Advanced Database Concepts", "Data Analytics with Python",
            "Web Development with HTML, CSS and JavaScript",
            "Backend Development", "Mobile Application Development",
            "Cloud Technologies", "Security in Applications",
            "Big Data Fundamentals", "IoT and Smart Systems",
        ],
    },
}


def seed_data(apps, schema_editor):
    AISathiClass = apps.get_model('school_app', 'AISathiClass')
    AISathiSubject = apps.get_model('school_app', 'AISathiSubject')
    AISathiChapter = apps.get_model('school_app', 'AISathiChapter')

    for class_order, (class_number, subjects) in enumerate(CURRICULUM.items()):
        cls_obj, _ = AISathiClass.objects.get_or_create(
            number=class_number,
            defaults={'order': class_order, 'is_active': True},
        )
        for subj_order, (subj_name, chapters) in enumerate(subjects.items()):
            subj_obj, _ = AISathiSubject.objects.get_or_create(
                class_ref=cls_obj,
                name=subj_name,
                defaults={'order': subj_order, 'is_active': True},
            )
            for ch_order, ch_name in enumerate(chapters):
                AISathiChapter.objects.get_or_create(
                    subject=subj_obj,
                    name=ch_name,
                    defaults={'order': ch_order, 'is_active': True},
                )


def unseed_data(apps, schema_editor):
    AISathiClass = apps.get_model('school_app', 'AISathiClass')
    AISathiClass.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('school_app', '0022_ai_sathi_tables'),
    ]

    operations = [
        migrations.RunPython(seed_data, reverse_code=unseed_data),
    ]
