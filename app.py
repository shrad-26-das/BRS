from flask import Flask, render_template, request, jsonify, redirect, url_for
import pickle
import numpy as np

# ── LOAD FILES ───────────────────────────────────────────────────────────────

popular_df        = pickle.load(open('popular.pkl',           'rb'))
pt                = pickle.load(open('pt.pkl',                'rb'))
books             = pickle.load(open('books.pkl',             'rb'))
similarity_scores = pickle.load(open('similarity_scores.pkl', 'rb'))

app = Flask(__name__)

# ── HELPER: build recommendations for a matched title ────────────────────────

def get_recommendations(matched_title):
    index = np.where(pt.index == matched_title)[0][0]

    similar_items = sorted(
        enumerate(similarity_scores[index]),
        key=lambda x: x[1],
        reverse=True
    )[1:9]

    recs = []
    for i, score in similar_items:
        tmp = books[books['Book-Title'] == pt.index[i]].drop_duplicates('Book-Title')
        if tmp.empty:
            continue
        recs.append({
            "title":  tmp['Book-Title'].values[0],
            "author": tmp['Book-Author'].values[0],
            "image":  tmp['Image-URL-M'].values[0],
        })
    return recs

# ── HOME PAGE ─────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template(
        'index.html',
        book_name = list(popular_df['Book-Title'].values),
        author    = list(popular_df['Book-Author'].values),
        image     = list(popular_df['Image-URL-M'].values),
        votes     = [int(v)            for v in popular_df['num_ratings'].values],
        rating    = [round(float(r),2) for r in popular_df['avg_rating'].values],
    )

# ── RECOMMEND PAGE ────────────────────────────────────────────────────────────

@app.route('/recommend')
def recommend_ui():
    return render_template('recommend.html')

# ── RECOMMEND FORM (POST) → redirect to book detail page ─────────────────────

@app.route('/recommend_books', methods=['POST'])
def recommend_books():
    user_input = (request.form.get('user_input') or '').strip()

    if not user_input:
        return render_template('recommend.html', error='Please enter a book name.')

    matches = [t for t in pt.index if user_input.lower() in t.lower()]

    if not matches:
        return render_template('recommend.html', error='Book not found. Try another title.')

    # Redirect to the detail page using the exact matched title
    return redirect(url_for('book_detail', title=matches[0]))

# ── BOOK DETAIL PAGE ──────────────────────────────────────────────────────────

@app.route('/book/<path:title>')
def book_detail(title):
    # Try exact match first, then fuzzy
    if title in pt.index:
        matched_title = title
    else:
        matches = [t for t in pt.index if title.lower() in t.lower()]
        if not matches:
            # Also search books df for display even if no similarity data
            matches_books = books[
                books['Book-Title'].str.contains(title, case=False, na=False)
            ].drop_duplicates('Book-Title')
            if matches_books.empty:
                return render_template('recommend.html', error='Book not found.')
            matched_title = matches_books['Book-Title'].values[0]
        else:
            matched_title = matches[0]

    # Selected book info
    sel_df = books[books['Book-Title'] == matched_title].drop_duplicates('Book-Title')
    if sel_df.empty:
        return render_template('recommend.html', error='Book not found.')

    selected_book = {
        "title":  sel_df['Book-Title'].values[0],
        "author": sel_df['Book-Author'].values[0],
        "image":  sel_df['Image-URL-M'].values[0],
    }

    # Popularity stats if available
    pop_row = popular_df[popular_df['Book-Title'] == matched_title]
    if not pop_row.empty:
        selected_book['rating'] = round(float(pop_row['avg_rating'].values[0]), 2)
        selected_book['votes']  = int(pop_row['num_ratings'].values[0])

    # Recommendations (only if title exists in pivot table)
    recs = []
    if matched_title in pt.index:
        recs = get_recommendations(matched_title)

    return render_template('book_detail.html', selected_book=selected_book, recs=recs)

# ── LIVE SEARCH SUGGESTIONS ───────────────────────────────────────────────────

@app.route('/search_suggestions')
def search_suggestions():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    matches = books[
        books['Book-Title'].str.contains(query, case=False, na=False)
    ].drop_duplicates('Book-Title').head(8)

    suggestions = []
    for _, row in matches.iterrows():
        suggestions.append({
            "title":  row['Book-Title'],
            "author": row['Book-Author'],
            "image":  row['Image-URL-M'],
        })
    return jsonify(suggestions)

# ── RUN ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True)