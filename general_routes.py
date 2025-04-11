from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, make_response

general_bp = Blueprint('general', __name__) # لا بادئة هنا، مسارات عامة في الجذر


@general_bp.route('/blog-details')
def blogdetails():
    return render_template('blog-details.html')

@general_bp.route('/blog')
def blog():
    return render_template('blog.html')

@general_bp.route('/contact')
def contact():
    return render_template('contact.html')