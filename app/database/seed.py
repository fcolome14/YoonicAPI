""" Load static data to database """
from sqlalchemy.orm import Session
import app.models as models

class Seed:
    @staticmethod
    def seed_data(db: Session):
        if db.query(models.Categories).count() == 0:
            Seed.add_categories(db)
        
        if db.query(models.StatusCodes).count() == 0:
            Seed.add_status_codes(db)
        
        if db.query(models.Subcategories).count() == 0:
            Seed.add_subcategories(db)
        
        if db.query(models.Tags).count() == 0:
            Seed.add_tags(db)
    
    @staticmethod
    def add_categories(db: Session):
        categories = [
            {"code": "cat.1", "name": "Sports"},
            {"code": "cat.2", "name": "Culture"},
            {"code": "cat.3", "name": "Tech"},
            {"code": "cat.4", "name": "Media"},
            {"code": "cat.5", "name": "Food"},
            {"code": "cat.6", "name": "Travel"},
            {"code": "cat.7", "name": "Fashion"},
            {"code": "cat.8", "name": "Health & Wellness"},
        ]
        category_models = [models.Categories(**cat) for cat in categories]
        db.add_all(category_models)
        db.commit()
        for category in category_models:
            db.refresh(category)
        print(f"Added {len(category_models)} categories.")

    @staticmethod
    def add_status_codes(db: Session):
        status_codes = ["staging", "revision", "active", "inactive", "reported"]
        code_models = [models.StatusCodes(name=code) for code in status_codes]
        db.add_all(code_models)
        db.commit()
        for code in code_models:
            db.refresh(code)
        print(f"Added {len(code_models)} status codes.")

    @staticmethod
    def add_subcategories(db: Session):
        subcategory_structure = {
            "cat.1": [
                "Team Sports", "Individual Sports", "Fitness", 
                "Outdoor Activities", "eSports"
            ],
            "cat.2": [
                "Arts", "Music", "Literature", 
                "Heritage & Traditions", "Festivals"
            ],
            "cat.3": [
                "Programming", "AI & Data", "Hardware", 
                "Startups", "Gaming"
            ],
            "cat.4": [
                "Social Media", "Photography", "Cinema", 
                "TV and Streaming", "News and Journalism"
            ],
            "cat.5": [
                "Cuisine Types", "Dietary Preferences", "Cooking and Recipes", 
                "Drinks", "Food Culture"
            ],
            "cat.6": [
                "Destinations", "Travel Styles", "Adventures", 
                "Cultural Exploration", "Travel Photography"
            ],
            "cat.7": [
                "Trends", "Clothing Types", "Accessories", 
                "Sustainable Fashion", "Beauty and Makeup"
            ],
            "cat.8": [
                "Physical Health", "Mental Health", "Nutrition", 
                "Lifestyle", "Alternative Therapies"
            ],
        }

        fetched_categories = db.query(models.Categories).all()
        category_map = {category.code: category for category in fetched_categories}

        subcategory_models = []
        for cat_code, sub_names in subcategory_structure.items():
            category = category_map.get(cat_code)
            if not category:
                print(f"Category with code {cat_code} not found, skipping.")
                continue
            
            for index, sub_name in enumerate(sub_names, start=1):
                sub_code = f"sub{cat_code}.{index}"
                subcategory_models.append(
                    models.Subcategories(
                        code=sub_code, 
                        name=sub_name, 
                        cat=category.id
                    )
                )

        db.add_all(subcategory_models)
        db.commit()
        for subcategory in subcategory_models:
            db.refresh(subcategory)
        print(f"Added {len(subcategory_models)} subcategories.")

    @staticmethod
    def add_tags(db: Session):
        tags_structure = {
            "subcat.1.1": [
                "Football", "Basketball", "Rugby", "Volleyball", "Cricket", 
                "Baseball", "Handball", "American Football", "Water Polo", "Ice Hockey"
            ],
            "subcat.1.2": [
                "Tennis", "Boxing", "Golf", "Martial Arts", "Swimming", 
                "Cycling", "Skiing", "Track and Field", "Archery", "Badminton"
            ],
            "subcat.1.3": [
                "Strength Training", "Cardio", "Yoga", "Pilates", "HIIT", 
                "CrossFit", "Running", "Zumba", "Boxing Fitness", "Spin Class"
            ],
            "subcat.1.4": [
                "Hiking", "Rock Climbing", "Camping", "Kayaking", "Cycling", 
                "Trail Running", "Fishing", "Snowboarding", "Surfing", "Canoeing"
            ],
            "subcat.1.5": [
                "League of Legends", "Fortnite", "Dota 2", "Valorant", "PUBG", 
                "Apex Legends", "Overwatch", "Minecraft", "Call of Duty", "FIFA"
            ],
            "subcat.2.1": [
                "Impressionism", "Renaissance Art", "Modern Art", "Surrealism", "Abstract Art", 
                "Cubism", "Baroque", "Pop Art", "Realism", "Street Art"
            ],
            "subcat.2.2": [
                "Rock", "Pop", "Classical", "Jazz", "Electronic", 
                "Hip Hop", "Country", "Reggae", "Blues", "Indie"
            ],
            "subcat.2.3": [
                "Fiction", "Poetry", "Drama", "Non-fiction", "Short Stories", 
                "Novels", "Historical Fiction", "Fantasy", "Science Fiction", "Biography"
            ],
            "subcat.2.4": [
                "Cultural Traditions", "Folklore", "Heritage Sites", "National Holidays", "Ancient Practices", 
                "Indigenous Cultures", "Festivals", "Music Traditions", "Cultural Celebrations", "World Heritage"
            ],
            "subcat.2.5": [
                "Music Festivals", "Cultural Festivals", "Film Festivals", "Food Festivals", "Art Exhibitions", 
                "Dance Festivals", "Theatre Festivals", "Literary Festivals", "Tech Festivals", "Startup Events"
            ],
            "subcat.3.1": [
                "Python", "JavaScript", "Ruby", "C#", "Go", 
                "Java", "PHP", "Swift", "Kotlin", "Rust"
            ],
            "subcat.3.2": [
                "Artificial Intelligence", "Data Science", "Machine Learning", "Deep Learning", "Natural Language Processing", 
                "Computer Vision", "Neural Networks", "Robotics", "Reinforcement Learning", "Predictive Analytics"
            ],
            "subcat.3.3": [
                "Processors", "Memory", "Motherboards", "Graphics Cards", "Peripherals", 
                "Networking", "Storage Devices", "Sound Cards", "Power Supplies", "Monitors"
            ],
            "subcat.3.4": [
                "Entrepreneurship", "Startups", "Venture Capital", "Business Models", "Tech Innovations", 
                "Disruptive Technologies", "Lean Startup", "Angel Investors", "Pitch Decks", "Business Strategy"
            ],
            "subcat.3.5": [
                "Gaming Consoles", "PC Gaming", "Esports", "Game Development", "Mobile Gaming", 
                "Virtual Reality", "Augmented Reality", "Game Streaming", "Retro Gaming", "Game Design"
            ],
            "subcat.4.1": [
                "Instagram", "Facebook", "Twitter", "LinkedIn", "TikTok", 
                "Snapchat", "YouTube", "Pinterest", "Reddit", "Tumblr"
            ],
            "subcat.4.2": [
                "Landscape Photography", "Portrait Photography", "Street Photography", "Wildlife Photography", "Event Photography", 
                "Astro Photography", "Sports Photography", "Fashion Photography", "Architectural Photography", "Food Photography"
            ],
            "subcat.4.3": [
                "Action Movies", "Drama", "Comedy", "Sci-Fi", "Horror", 
                "Thriller", "Romance", "Documentary", "Fantasy", "Animated Films"
            ],
            "subcat.4.4": [
                "Netflix", "HBO", "Disney+", "Amazon Prime", "YouTube", 
                "Apple TV+", "Hulu", "BBC iPlayer", "Peacock", "Paramount+"
            ],
            "subcat.4.5": [
                "Breaking News", "Investigative Journalism", "Political Reporting", "Sports Journalism", "Cultural Reporting", 
                "Tech News", "Business News", "Entertainment News", "Health Reporting", "Environmental Journalism"
            ],
            "subcat.5.1": [
                "Italian Cuisine", "Chinese Cuisine", "Mexican Cuisine", "Indian Cuisine", "French Cuisine", 
                "Japanese Cuisine", "Greek Cuisine", "Spanish Cuisine", "Thai Cuisine", "Middle Eastern Cuisine"
            ],
            "subcat.5.2": [
                "Vegan", "Gluten-Free", "Keto", "Low-Carb", "Paleo", 
                "Mediterranean", "Whole30", "Diabetic-Friendly", "Raw Food", "Intermittent Fasting"
            ],
            "subcat.5.3": [
                "Baking", "Grilling", "Roasting", "Frying", "Steaming", 
                "Boiling", "Slow Cooking", "Sous-Vide", "Stir-Frying", "Barbecuing"
            ],
            "subcat.5.4": [
                "Cocktails", "Juices", "Smoothies", "Coffee", "Tea", 
                "Mocktails", "Beer", "Wine", "Whiskey", "Cocktail Recipes"
            ],
            "subcat.5.5": [
                "Food Traditions", "Street Food", "Farm-to-Table", "Food Pairing", "Food Festivals", 
                "Food Photography", "Food Styling", "Food Blogging", "Global Cuisines", "Sustainable Eating"
            ],
            "subcat.6.1": [
                "Paris", "New York City", "Tokyo", "Rome", "London", 
                "Dubai", "Barcelona", "Sydney", "Istanbul", "Berlin"
            ],
            "subcat.6.2": [
                "Luxury Travel", "Adventure Travel", "Budget Travel", "Solo Travel", "Group Travel", 
                "Eco-Tourism", "Cultural Tourism", "Road Trips", "Cruises", "Business Travel"
            ],
            "subcat.6.3": [
                "Hiking", "Safari", "Backpacking", "Road Trips", "Mountain Climbing", 
                "Scuba Diving", "Skiing", "Snowboarding", "Surfing", "Cycling Tours"
            ],
            "subcat.6.4": [
                "Cultural Immersion", "Local Cuisine", "Traditional Clothing", "Heritage Tours", "Museum Visits", 
                "Historical Tours", "Art Tours", "Religious Sites", "Folk Music", "Language Learning"
            ],
            "subcat.6.5": [
                "Travel Photography", "Travel Vlogging", "Landscape Photography", "City Photography", "Cultural Photography", 
                "Food Photography", "Adventure Photography", "Wildlife Photography", "Drone Photography", "Travel Blog"
            ],
            "subcat.7.1": [
                "Minimalism", "Sustainability", "Upcycling", "Fast Fashion", "DIY Fashion", 
                "Eco-Friendly Fashion", "Vintage Clothing", "Thrift Shopping", "Street Style", "Recycled Materials"
            ],
            "subcat.7.2": [
                "Casual Wear", "Formal Wear", "Sportswear", "Winter Wear", "Beachwear", 
                "Party Wear", "Business Attire", "Activewear", "Sleepwear", "Loungewear"
            ],
            "subcat.7.3": [
                "Jewelry", "Bags", "Hats", "Shoes", "Scarves", 
                "Watches", "Sunglasses", "Belts", "Hair Accessories", "Gloves"
            ],
            "subcat.7.4": [
                "Ethical Fashion", "Recycled Fabrics", "Organic Cotton", "Slow Fashion", "Eco-friendly Materials", 
                "Fair Trade", "Upcycled Fashion", "Vegan Leather", "Conscious Consumption", "Circular Economy"
            ],
            "subcat.7.5": [
                "Makeup Trends", "Beauty Products", "Skincare", "Haircare", "Nail Art", 
                "Fragrances", "Cosmetic Surgery", "Beauty Routines", "Beauty Bloggers", "Anti-aging"
            ],
            "subcat.8.1": [
                "Strength Training", "Running", "Yoga", "Pilates", "Cycling", 
                "Weightlifting", "Bodybuilding", "CrossFit", "Jump Rope", "Stretching"
            ],
            "subcat.8.2": [
                "Meditation", "Mindfulness", "Therapy", "Stress Management", "Breathing Exercises", 
                "Cognitive Behavioral Therapy", "Emotional Health", "Journaling", "Gratitude Practice", "Relaxation Techniques"
            ],
            "subcat.8.3": [
                "Healthy Eating", "Diet Plans", "Superfoods", "Organic Food", "Meal Prep", 
                "Vitamins", "Low-carb Diets", "High-protein Diets", "Plant-based Diet", "Meal Delivery Services"
            ],
            "subcat.8.4": [
                "Sleep Hygiene", "Work-Life Balance", "Time Management", "Productivity", "Self-care", 
                "Stress Relief", "Positive Thinking", "Life Coaching", "Mental Clarity", "Motivation"
            ],
            "subcat.8.5": [
                "Acupuncture", "Massage Therapy", "Aromatherapy", "Chiropractic", "Herbal Remedies", 
                "Reiki", "Reflexology", "Cupping Therapy", "Holistic Healing", "Alternative Medicine"
            ],
        }


        fetched_subcategories = db.query(models.Subcategories).all()
        subcategory_map = {subcategory.code: subcategory for subcategory in fetched_subcategories}

        tag_models = []
        for subcat_code, tag_names in tags_structure.items():
            subcategory = subcategory_map.get(subcat_code)
            if not subcategory:
                print(f"Subcategory with code {subcat_code} not found, skipping.")
                continue
            
            for index, sub_name in enumerate(tag_names, start=1):
                sub_code = f"sub{subcat_code}.{index}"
                tag_models.append(
                    models.Tags(
                        name=sub_name, 
                        subcat=subcategory.id,
                        weight=1
                    )
                )

        db.add_all(tag_models)
        db.commit()
        for subcategory in tag_models:
            db.refresh(subcategory)
        print(f"Added {len(tag_models)} tags.")
