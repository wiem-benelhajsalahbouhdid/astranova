from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from datetime import datetime, timedelta
import json, os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'astranova-secret-2025')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///astranova.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
CORS(app)

# ─────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    # Education
    university = db.Column(db.String(200))
    faculty = db.Column(db.String(150))        # e.g. "Faculty of Engineering"
    field_of_study = db.Column(db.String(100)) # e.g. "Computer Science"
    degree = db.Column(db.String(50))          # Bachelor / Master / PhD
    year_of_study = db.Column(db.String(20))
    gpa = db.Column(db.Float)
    weekly_hours = db.Column(db.String(20))
    # Path
    path_type = db.Column(db.String(20))       # 'focused' | 'explorer'
    target_role = db.Column(db.String(150))
    target_industry = db.Column(db.String(100))
    # Personality
    personality_type = db.Column(db.String(50))
    personality_traits = db.Column(db.Text, default='[]')
    habit_score = db.Column(db.Text, default='{}')  # JSON: {focus, consistency, curiosity}
    # Gamification
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    streak = db.Column(db.Integer, default=0)
    avatar = db.Column(db.String(10), default='🧙‍♀️')
    badges = db.Column(db.Text, default='[]')
    # Status
    is_premium = db.Column(db.Boolean, default=False)
    onboarding_step = db.Column(db.Integer, default=0)  # 0-6
    onboarding_completed = db.Column(db.Boolean, default=False)
    # CV & LinkedIn
    cv_data = db.Column(db.Text, default='{}')
    linkedin_token = db.Column(db.String(500))
    # Relationships
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    roadmap_nodes = db.relationship('RoadmapNode', backref='user', lazy=True)
    skills = db.relationship('UserSkill', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)


class RoadmapNode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # 'career' | 'academic' | 'soft'
    status = db.Column(db.String(20), default='locked')
    order_index = db.Column(db.Integer)
    xp_reward = db.Column(db.Integer, default=100)
    resources = db.Column(db.Text, default='[]')
    skills_list = db.Column(db.Text, default='[]')
    progress = db.Column(db.Integer, default=0)
    test_score = db.Column(db.Integer)
    completed_at = db.Column(db.DateTime)
    difficulty = db.Column(db.String(20), default='medium')
    planet_type = db.Column(db.String(30), default='rocky')  # visual style


class AcademicPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(150))
    importance = db.Column(db.String(20))   # critical / high / medium / low
    career_relevance = db.Column(db.Text)
    study_tips = db.Column(db.Text)
    weight_in_degree = db.Column(db.Float)
    ai_recommendation = db.Column(db.Text)


class UserSkill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100))
    level = db.Column(db.String(20), default='beginner')
    score = db.Column(db.Integer, default=0)
    verified = db.Column(db.Boolean, default=False)
    certified = db.Column(db.Boolean, default=False)
    certification_name = db.Column(db.String(200))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)


class Opportunity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    company = db.Column(db.String(100))
    location = db.Column(db.String(100))
    type = db.Column(db.String(50))
    required_skills = db.Column(db.Text, default='[]')
    is_premium = db.Column(db.Boolean, default=False)
    url = db.Column(db.String(500))
    salary = db.Column(db.String(100))
    posted_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(50))
    title = db.Column(db.String(200))
    message = db.Column(db.Text)
    read = db.Column(db.Boolean, default=False)
    is_premium = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class WeeklyMeeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    scheduled_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')
    trigger_reason = db.Column(db.String(200))
    notes = db.Column(db.Text)


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    role = db.Column(db.String(10))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409
    pw = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(email=data['email'], password_hash=pw,
                first_name=data.get('first_name',''), last_name=data.get('last_name',''))
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    return jsonify({'success': True, 'redirect': '/onboarding'}), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    session['user_id'] = user.id
    dest = '/dashboard' if user.onboarding_completed else '/onboarding'
    return jsonify({'success': True, 'redirect': dest, 'user': _user_dict(user)})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


# ─────────────────────────────────────────────
# ONBOARDING (6 steps)
# ─────────────────────────────────────────────

@app.route('/api/onboarding/step', methods=['POST'])
def onboarding_step():
    """Universal onboarding step handler."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    data = request.get_json()
    step = data.get('step')
    xp_earned = 0

    if step == 1:  # Basic profile
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.avatar = data.get('avatar', user.avatar)
        xp_earned = 30

    elif step == 2:  # Education details
        user.university = data.get('university')
        user.faculty = data.get('faculty')
        user.field_of_study = data.get('field_of_study')
        user.degree = data.get('degree')
        user.year_of_study = data.get('year_of_study')
        user.gpa = data.get('gpa')
        user.weekly_hours = data.get('weekly_hours')
        xp_earned = 50

    elif step == 3:  # Habit & personality quiz
        user.personality_type = data.get('personality_type')
        user.personality_traits = json.dumps(data.get('traits', []))
        user.habit_score = json.dumps(data.get('habit_scores', {}))
        xp_earned = 150

    elif step == 4:  # Skills self-assessment
        for skill_data in data.get('skills', []):
            existing = UserSkill.query.filter_by(
                user_id=user.id, name=skill_data['name']).first()
            if existing:
                existing.level = skill_data['level']
                existing.score = skill_data.get('score', 50)
            else:
                s = UserSkill(user_id=user.id, name=skill_data['name'],
                              level=skill_data['level'], score=skill_data.get('score', 50))
                db.session.add(s)
        xp_earned = 80

    elif step == 5:  # Path choice
        user.path_type = data.get('path_type')
        user.target_role = data.get('target_role', '')
        user.target_industry = data.get('target_industry', '')
        xp_earned = 50

    elif step == 6:  # Finalize — generate everything
        _generate_roadmap(user)
        _generate_academic_plan(user)
        user.onboarding_completed = True
        xp_earned = 200
        # Welcome notification
        n = Notification(user_id=user.id, type='achievement',
            title='🚀 Welcome to ASTRANOVA!',
            message=f'Your personalized roadmap is ready, {user.first_name}! Start your first mission.')
        db.session.add(n)

    user.xp += xp_earned
    user.level = max(1, user.xp // 500 + 1)
    user.onboarding_step = step
    db.session.commit()
    return jsonify({'success': True, 'xp': user.xp, 'xp_earned': xp_earned,
                    'redirect': '/dashboard' if step == 6 else None})


@app.route('/api/onboarding/career-analysis', methods=['POST'])
def career_analysis():
    """For 'explorer' users: AI job market analysis based on profile."""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    # In production: call AI API with user profile
    analysis = _generate_career_analysis(user)
    return jsonify({'analysis': analysis})


def _generate_career_analysis(user):
    """Stub — replace with real AI call."""
    field = user.field_of_study or 'Computer Science'
    personality = user.personality_type or 'Analytical'
    careers_map = {
        'Computer Science': [
            {'role': 'Frontend Developer', 'match': 91, 'demand': 'Very High',
             'avg_salary': '2,500–4,000 TND/mo', 'reason': f'Your {personality} personality and CS background align perfectly with UI/UX problem solving.'},
            {'role': 'Data Scientist', 'match': 84, 'demand': 'High',
             'avg_salary': '3,000–5,000 TND/mo', 'reason': 'Growing field in MENA region with strong demand.'},
            {'role': 'Backend Engineer', 'match': 78, 'demand': 'Very High',
             'avg_salary': '2,800–4,500 TND/mo', 'reason': 'Core engineering skills transfer directly.'},
        ],
        'Business': [
            {'role': 'Product Manager', 'match': 88, 'demand': 'High',
             'avg_salary': '2,000–3,500 TND/mo', 'reason': 'Business + analytical skills are ideal for PM roles.'},
            {'role': 'Digital Marketing Specialist', 'match': 82, 'demand': 'High',
             'avg_salary': '1,500–2,500 TND/mo', 'reason': 'Growing demand for data-driven marketers.'},
        ]
    }
    roles = careers_map.get(field, careers_map['Computer Science'])
    return {
        'top_careers': roles,
        'market_summary': f'The {field} job market in Tunisia & MENA is growing at ~18% annually. Demand is especially high in tech startups and remote-first companies.',
        'personality_insight': f'As a {personality} type, you thrive in structured environments with clear goals. Roles that blend creativity with logic suit you best.',
        'recommended_role': roles[0]['role'] if roles else 'Software Developer'
    }


# ─────────────────────────────────────────────
# ROADMAP GENERATION
# ─────────────────────────────────────────────

ROADMAP_TEMPLATES = {
    'Frontend Developer': [
        {'title': 'HTML & CSS Mastery', 'skills': ['HTML5','CSS3','Flexbox','Grid','Responsive'], 'planet': 'earth', 'xp': 100},
        {'title': 'JavaScript Essentials', 'skills': ['ES6+','DOM','Async','Fetch'], 'planet': 'mars', 'xp': 150},
        {'title': 'React.js', 'skills': ['Components','Hooks','Router','Redux'], 'planet': 'neptune', 'xp': 200},
        {'title': 'TypeScript', 'skills': ['Types','Interfaces','Generics'], 'planet': 'saturn', 'xp': 200},
        {'title': 'Testing & QA', 'skills': ['Jest','RTL','Cypress'], 'planet': 'moon', 'xp': 150},
        {'title': 'Portfolio & Job Hunt', 'skills': ['Portfolio','LinkedIn','Interviews'], 'planet': 'star', 'xp': 300},
    ],
    'Data Scientist': [
        {'title': 'Python Fundamentals', 'skills': ['Python','Pandas','NumPy'], 'planet': 'earth', 'xp': 100},
        {'title': 'Data Analysis', 'skills': ['Visualization','Matplotlib','Seaborn'], 'planet': 'mars', 'xp': 150},
        {'title': 'Machine Learning', 'skills': ['Scikit-learn','Models','Evaluation'], 'planet': 'neptune', 'xp': 250},
        {'title': 'Deep Learning', 'skills': ['TensorFlow','PyTorch','Neural Nets'], 'planet': 'saturn', 'xp': 300},
        {'title': 'Projects & Portfolio', 'skills': ['Kaggle','GitHub','Papers'], 'planet': 'star', 'xp': 300},
    ],
    'default': [
        {'title': 'Foundation Skills', 'skills': ['Core Concepts','Basics'], 'planet': 'earth', 'xp': 100},
        {'title': 'Intermediate Level', 'skills': ['Advanced Skills'], 'planet': 'mars', 'xp': 150},
        {'title': 'Specialization', 'skills': ['Domain Expertise'], 'planet': 'neptune', 'xp': 200},
        {'title': 'Real Projects', 'skills': ['Portfolio Projects'], 'planet': 'saturn', 'xp': 250},
        {'title': 'Career Launch', 'skills': ['Applications','Interviews'], 'planet': 'star', 'xp': 300},
    ]
}

def _generate_roadmap(user):
    role = user.target_role or 'default'
    template = ROADMAP_TEMPLATES.get(role, ROADMAP_TEMPLATES['default'])
    existing_skills = {s.name.lower() for s in user.skills}
    for i, t in enumerate(template):
        has_skills = any(s.lower() in existing_skills for s in t['skills'])
        status = 'done' if (i == 0 and has_skills) else ('active' if i == 0 else 'locked')
        node = RoadmapNode(
            user_id=user.id, title=t['title'],
            skills_list=json.dumps(t['skills']),
            status=status, order_index=i,
            xp_reward=t['xp'], planet_type=t['planet'],
            progress=100 if status == 'done' else 0
        )
        db.session.add(node)

def _generate_academic_plan(user):
    """Generate academic subject importance plan."""
    field = user.field_of_study or 'Computer Science'
    role = user.target_role or ''
    plans_map = {
        'Computer Science': [
            {'subject': 'Algorithms & Data Structures', 'importance': 'critical',
             'career_relevance': 'Core requirement for all tech interviews',
             'study_tips': 'Practice on LeetCode daily. Focus on arrays, trees, graphs.',
             'weight': 0.95},
            {'subject': 'Operating Systems', 'importance': 'high',
             'career_relevance': 'Essential for backend & systems roles',
             'study_tips': 'Focus on processes, memory management, concurrency.',
             'weight': 0.75},
            {'subject': 'Database Systems', 'importance': 'high',
             'career_relevance': 'Every software job needs SQL knowledge',
             'study_tips': 'Build real projects with PostgreSQL or MySQL.',
             'weight': 0.80},
            {'subject': 'Software Engineering', 'importance': 'critical',
             'career_relevance': 'Design patterns & agile are used in every company',
             'study_tips': 'Learn Git, agile methodology, and clean code principles.',
             'weight': 0.90},
            {'subject': 'Mathematics / Discrete Math', 'importance': 'medium',
             'career_relevance': 'Important for AI/ML paths',
             'study_tips': 'Focus on logic, sets, and graph theory.',
             'weight': 0.60},
        ]
    }
    for plan_data in plans_map.get(field, plans_map.get('Computer Science', [])):
        plan = AcademicPlan(
            user_id=user.id,
            subject=plan_data['subject'],
            importance=plan_data['importance'],
            career_relevance=plan_data['career_relevance'],
            study_tips=plan_data['study_tips'],
            weight_in_degree=plan_data['weight'],
            ai_recommendation=f"For your goal of becoming a {role}, this subject is rated {plan_data['importance']}."
        )
        db.session.add(plan)


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    nodes = RoadmapNode.query.filter_by(user_id=user.id).order_by(RoadmapNode.order_index).all()
    skills = UserSkill.query.filter_by(user_id=user.id).all()
    notifs = Notification.query.filter_by(user_id=user.id, read=False).limit(10).all()
    academic = AcademicPlan.query.filter_by(user_id=user.id).all()
    opps = _get_opportunities(user)
    return jsonify({
        'user': _user_dict(user),
        'roadmap': [_node_dict(n) for n in nodes],
        'skills': [_skill_dict(s) for s in skills],
        'notifications': [_notif_dict(n) for n in notifs],
        'academic_plan': [_academic_dict(a) for a in academic],
        'opportunities': opps
    })


# ─────────────────────────────────────────────
# ROADMAP ACTIONS
# ─────────────────────────────────────────────

@app.route('/api/roadmap/update', methods=['POST'])
def update_roadmap():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    node = RoadmapNode.query.get(data['node_id'])
    if node.user_id != session['user_id']:
        return jsonify({'error': 'Forbidden'}), 403
    node.progress = min(100, data.get('progress', node.progress))
    if node.progress >= 100:
        node.status = 'done'
        node.completed_at = datetime.utcnow()
        user = User.query.get(session['user_id'])
        user.xp += node.xp_reward
        user.level = user.xp // 500 + 1
        _unlock_next(node)
        _update_cv(user, node)
        _check_weekly_meeting(user)
    db.session.commit()
    return jsonify({'success': True, 'xp': User.query.get(session['user_id']).xp})


@app.route('/api/roadmap/test', methods=['POST'])
def submit_test():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    node = RoadmapNode.query.get(data['node_id'])
    score = data['score']
    node.test_score = score
    user = User.query.get(session['user_id'])
    new_opps = 0
    if score >= 70:
        node.status = 'done'
        node.progress = 100
        node.completed_at = datetime.utcnow()
        user.xp += node.xp_reward
        user.level = user.xp // 500 + 1
        _unlock_next(node)
        _update_cv(user, node)
        new_opps = _match_and_notify(user)
    db.session.commit()
    return jsonify({'success': True, 'passed': score >= 70, 'score': score,
                    'xp': user.xp, 'new_opportunities': new_opps})


@app.route('/api/roadmap/difficulty', methods=['POST'])
def change_difficulty():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    data = request.get_json()
    difficulty = data.get('difficulty', 'medium')
    # Adjust locked nodes
    locked = RoadmapNode.query.filter_by(user_id=user.id, status='locked').all()
    for node in locked:
        node.difficulty = difficulty
        if difficulty == 'easy':
            node.xp_reward = int(node.xp_reward * 0.7)
        elif difficulty == 'hard':
            node.xp_reward = int(node.xp_reward * 1.4)
    db.session.commit()
    return jsonify({'success': True, 'difficulty': difficulty})


# ─────────────────────────────────────────────
# ALI CHATBOT
# ─────────────────────────────────────────────

@app.route('/api/ali/chat', methods=['POST'])
def ali_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    data = request.get_json()
    msg = data.get('message', '')
    db.session.add(ChatMessage(user_id=user.id, role='user', content=msg))
    response = _ali_respond(user, msg)
    db.session.add(ChatMessage(user_id=user.id, role='ali', content=response))
    db.session.commit()
    return jsonify({'response': response, 'xp_reward': 5})


def _ali_respond(user, message):
    name = user.first_name or 'Explorer'
    msg = message.lower()
    active_node = next((n for n in user.roadmap_nodes if n.status == 'active'), None)
    node_title = active_node.title if active_node else 'your next mission'
    if any(w in msg for w in ['hello','hi','hey','salut','bonjour','salam']):
        return f"Hey {name}! 🌟 I'm Ali, your ASTRANOVA co-pilot. Your mission control is online! You're Level {user.level} with {user.xp} XP. Ready to conquer the galaxy? ✨"
    if any(w in msg for w in ['roadmap','next','mission','planet']):
        return f"Your current mission: **{node_title}** — you're making great progress! Complete it to unlock the next planet and earn +{active_node.xp_reward if active_node else 150} XP. Keep going, {name}! 🚀"
    if any(w in msg for w in ['job','opportunity','work','intern','career']):
        return f"I've been scanning the galaxy for opportunities, {name}! Based on your skills, there are 4 matches — 2 at 80%+ compatibility. Want me to auto-apply with your updated CV? 💼"
    if any(w in msg for w in ['cv','resume','linkedin']):
        return f"Your CV is auto-synced with every skill you master, {name}! You have {len(user.skills)} verified skills. Want to add a certification? That'll unlock premium opportunities 🏆"
    if any(w in msg for w in ['study','university','faculty','subject','course']):
        return f"Based on your {user.field_of_study or 'field'} curriculum, I've analyzed which subjects matter most for your career goal. Check the Academic Plan section — it's your secret weapon! 📚"
    if any(w in msg for w in ['streak','xp','level','point','score']):
        return f"You're at Level {user.level} with {user.xp} XP and a {user.streak}-day streak! 🔥 You need {500 - (user.xp % 500)} XP to reach Level {user.level + 1}. Every mission completed gets you closer! ⚡"
    if any(w in msg for w in ['skill','test','quiz']):
        return f"Ready to test your skills in {node_title}, {name}? Pass with 70%+ to verify the skill, update your CV, and unlock new job matches. It's time to level up! 🎯"
    return f"I hear you, {name}! As your AI navigator, my recommendation: focus on {node_title} today. Small consistent steps build empires. You've got this — the stars are literally the limit! 🌠"


# ─────────────────────────────────────────────
# CV
# ─────────────────────────────────────────────

def _update_cv(user, node):
    cv = json.loads(user.cv_data or '{}')
    cv.setdefault('skills', [])
    for s in json.loads(node.skills_list or '[]'):
        if s not in cv['skills']:
            cv['skills'].append(s)
    cv['last_updated'] = datetime.utcnow().isoformat()
    user.cv_data = json.dumps(cv)


@app.route('/api/cv/add-cert', methods=['POST'])
def add_cert():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    data = request.get_json()
    cv = json.loads(user.cv_data or '{}')
    cv.setdefault('certifications', [])
    cert = {'name': data['name'], 'issuer': data.get('issuer',''), 'date': datetime.utcnow().strftime('%b %Y')}
    cv['certifications'].append(cert)
    cv.setdefault('skills', [])
    for s in data.get('skills', []):
        if s not in cv['skills']:
            cv['skills'].append(s)
    user.cv_data = json.dumps(cv)
    skill = UserSkill(user_id=user.id, name=data['name'], certified=True,
                      certification_name=data['name'], verified=True, level='intermediate')
    db.session.add(skill)
    _match_and_notify(user)
    db.session.commit()
    return jsonify({'success': True, 'cv': cv,
                    'linkedin_post': _gen_li_post(user, cert)})


@app.route('/api/cv', methods=['GET'])
def get_cv():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    return jsonify(json.loads(user.cv_data or '{}'))


# ─────────────────────────────────────────────
# OPPORTUNITIES
# ─────────────────────────────────────────────

def _get_opportunities(user):
    skills = [s.name for s in user.skills]
    opps = Opportunity.query.all()
    result = []
    for o in opps:
        req = json.loads(o.required_skills)
        match = int(len(set(skills) & set(req)) / max(len(req), 1) * 100) if req else 50
        result.append({**_opp_dict(o), 'match_score': match})
    return sorted(result, key=lambda x: x['match_score'], reverse=True)[:10]


def _match_and_notify(user):
    opps = _get_opportunities(user)
    high = [o for o in opps if o['match_score'] >= 75]
    for o in high[:2]:
        db.session.add(Notification(user_id=user.id, type='opportunity',
            title=f"🎯 {o['match_score']}% match: {o['title']}",
            message=f"{o['company']} is hiring and your skills fit perfectly!",
            is_premium=o['is_premium']))
    return len(high)


@app.route('/api/opportunities/apply', methods=['POST'])
def auto_apply():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    if not user.is_premium:
        return jsonify({'error': 'Premium feature'}), 403
    return jsonify({'success': True, 'message': 'Applied with your latest CV! 🚀'})


# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────

@app.route('/api/notifications', methods=['GET'])
def get_notifs():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    notifs = Notification.query.filter_by(user_id=session['user_id']).order_by(
        Notification.created_at.desc()).limit(20).all()
    return jsonify([_notif_dict(n) for n in notifs])


@app.route('/api/notifications/<int:nid>/read', methods=['POST'])
def mark_read(nid):
    n = Notification.query.get(nid)
    if n and n.user_id == session.get('user_id'):
        n.read = True
        db.session.commit()
    return jsonify({'success': True})


# ─────────────────────────────────────────────
# WEEKLY MEETING
# ─────────────────────────────────────────────

def _check_weekly_meeting(user):
    if not user.is_premium:
        return
    week_ago = datetime.utcnow() - timedelta(days=7)
    completions = RoadmapNode.query.filter(
        RoadmapNode.user_id == user.id,
        RoadmapNode.completed_at >= week_ago).count()
    if completions == 0:
        meeting = WeeklyMeeting(user_id=user.id,
            scheduled_at=datetime.utcnow() + timedelta(days=1),
            trigger_reason='No tasks completed this week')
        db.session.add(meeting)
        db.session.add(Notification(user_id=user.id, type='meeting',
            title='⏰ Ali wants to check in',
            message="You haven't completed tasks this week. Ali scheduled a motivational session!",
            is_premium=True))


@app.route('/api/meetings', methods=['GET'])
def get_meetings():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    if not user.is_premium:
        return jsonify({'error': 'Premium feature'}), 403
    meetings = WeeklyMeeting.query.filter_by(user_id=user.id).all()
    return jsonify([{'id': m.id, 'scheduled_at': m.scheduled_at.isoformat(),
                     'status': m.status, 'reason': m.trigger_reason} for m in meetings])


# ─────────────────────────────────────────────
# PREMIUM
# ─────────────────────────────────────────────

@app.route('/api/upgrade', methods=['POST'])
def upgrade():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    user = User.query.get(session['user_id'])
    user.is_premium = True
    user.xp += 500
    db.session.commit()
    return jsonify({'success': True})


# ─────────────────────────────────────────────
# LINKEDIN
# ─────────────────────────────────────────────

def _gen_li_post(user, cert):
    return {
        'text': f"Thrilled to share I just earned the **{cert['name']}** certification! 🏆\n\nThis is a major milestone in my journey toward becoming a {user.target_role or 'tech professional'}. Every skill mastered, every level unlocked brings me closer to my constellation! 🌟\n\n#LearningInPublic #CareerGrowth #{(user.field_of_study or 'Tech').replace(' ','')}",
        'ready': True
    }


@app.route('/api/linkedin/post', methods=['POST'])
def li_post():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    # In production: use LinkedIn OAuth API
    return jsonify({'success': True, 'message': 'Posted to LinkedIn! 🎉'})


# ─────────────────────────────────────────────
# PAGE ROUTES
# ─────────────────────────────────────────────

@app.route('/') 
def index():
    return render_template('login.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/onboarding')
def onboarding_page():
    return render_template('onboarding.html')

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _user_dict(u):
    return {'id': u.id, 'email': u.email, 'first_name': u.first_name, 'last_name': u.last_name,
            'university': u.university, 'faculty': u.faculty, 'field_of_study': u.field_of_study,
            'degree': u.degree, 'year_of_study': u.year_of_study, 'target_role': u.target_role,
            'xp': u.xp, 'level': u.level, 'streak': u.streak, 'avatar': u.avatar,
            'is_premium': u.is_premium, 'personality_type': u.personality_type,
            'path_type': u.path_type, 'onboarding_completed': u.onboarding_completed,
            'onboarding_step': u.onboarding_step}

def _node_dict(n):
    return {'id': n.id, 'title': n.title, 'description': n.description, 'status': n.status,
            'order_index': n.order_index, 'xp_reward': n.xp_reward, 'progress': n.progress,
            'test_score': n.test_score, 'difficulty': n.difficulty, 'planet_type': n.planet_type,
            'skills': json.loads(n.skills_list or '[]'),
            'completed_at': n.completed_at.isoformat() if n.completed_at else None}

def _skill_dict(s):
    return {'id': s.id, 'name': s.name, 'level': s.level, 'score': s.score,
            'verified': s.verified, 'certified': s.certified}

def _opp_dict(o):
    return {'id': o.id, 'title': o.title, 'company': o.company, 'location': o.location,
            'type': o.type, 'salary': o.salary, 'is_premium': o.is_premium,
            'required_skills': json.loads(o.required_skills or '[]'),
            'posted_at': o.posted_at.strftime('%b %d') if o.posted_at else ''}

def _notif_dict(n):
    return {'id': n.id, 'type': n.type, 'title': n.title, 'message': n.message,
            'read': n.read, 'is_premium': n.is_premium,
            'created_at': n.created_at.strftime('%b %d')}

def _academic_dict(a):
    return {'id': a.id, 'subject': a.subject, 'importance': a.importance,
            'career_relevance': a.career_relevance, 'study_tips': a.study_tips,
            'weight': a.weight_in_degree, 'recommendation': a.ai_recommendation}

def _unlock_next(node):
    nxt = RoadmapNode.query.filter_by(
        user_id=node.user_id, order_index=node.order_index + 1).first()
    if nxt and nxt.status == 'locked':
        nxt.status = 'active'


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if Opportunity.query.count() == 0:
            opps = [
                Opportunity(title='Frontend Developer Intern', company='Vermeg', location='Tunis',
                    type='internship', required_skills=json.dumps(['React','JavaScript','CSS3']),
                    is_premium=False, salary='600 TND/mo'),
                Opportunity(title='React Developer', company='Instadeep', location='Tunis',
                    type='job', required_skills=json.dumps(['React','TypeScript','Redux']),
                    is_premium=True, salary='2,500–3,500 TND/mo'),
                Opportunity(title='Junior Frontend Engineer', company='Sofrecom', location='Tunis',
                    type='job', required_skills=json.dumps(['React','JavaScript','Git']),
                    is_premium=True, salary='2,000–3,000 TND/mo'),
                Opportunity(title='UI Developer (Remote)', company='Remote First', location='Remote',
                    type='freelance', required_skills=json.dumps(['HTML5','CSS3','JavaScript']),
                    is_premium=False, salary='Negotiable'),
            ]
            for o in opps: db.session.add(o)
            db.session.commit()
    app.run(debug=True, port=5000)
