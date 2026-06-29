def enrich(session, users):
    for u in users:
        u.profile = session.query(Profile).filter_by(user_id=u.id).first()
    return users
