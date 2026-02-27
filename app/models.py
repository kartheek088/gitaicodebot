from .database import get_connection


def save_installation(installation_id, repo_full_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO installations (installation_id, repo_full_name) VALUES (?, ?)",
        (installation_id, repo_full_name)
    )
    conn.commit()
    conn.close()


def review_exists(repo_full_name, pr_number, commit_sha):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id FROM reviews
        WHERE repo_full_name=? AND pr_number=? AND commit_sha=?
        """,
        (repo_full_name, pr_number, commit_sha)
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


def save_review(repo_full_name, pr_number, commit_sha, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO reviews (repo_full_name, pr_number, commit_sha, status)
        VALUES (?, ?, ?, ?)
        """,
        (repo_full_name, pr_number, commit_sha, status)
    )
    conn.commit()
    conn.close()