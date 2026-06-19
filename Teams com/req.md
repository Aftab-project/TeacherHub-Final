You are acting as a senior software engineer and mentor helping me build my final-year Computer Science project.

IMPORTANT CONTEXT:
- This project is for a university assessment and should be realistic for a final-year undergraduate student.
- Do NOT overcomplicate the implementation or make it look like enterprise-level software.
- Prefer simple, understandable technologies over advanced frameworks where possible.
- Use HTML, CSS, vanilla JavaScript, and Python (Flask or Django) unless there is a strong reason to use something else.
- Avoid React, Next.js, microservices, Kubernetes, or unnecessary complexity unless I explicitly ask for them.
- The code should be clean, modular, well-commented, and easy for me to understand and explain in my project demonstration.

PROJECT TO BUILD:
Create a web-based Team Collaboration Platform inspired by Microsoft Teams with the following features:
1. User registration and login.
2. Secure authentication and logout.
3. User profiles.
4. Create and manage teams.
5. Join teams through invitations or codes.
6. Team chat functionality.
7. Direct messaging between users.
8. File upload and sharing within teams.
9. Task management with status tracking.
10. Notifications for important events.
11. Role-based access control (e.g. Admin and Member).
12. Search for messages and files.
13. Responsive user interface.
14. Basic AI assistant to summarise conversations or answer FAQs if feasible.

GENERAL DEVELOPMENT RULES:
- Build incrementally.
- Never skip steps.
- Ensure every feature works before moving to the next.
- Use reusable code where appropriate.
- Keep the project maintainable.
- Prioritise readability over cleverness.
- Use secure coding practices and validate inputs.
- Hash passwords and avoid storing sensitive data insecurely.
- Include sensible error handling.

VERY IMPORTANT DOCUMENTATION REQUIREMENTS:
For EVERY change, addition, improvement, bug fix, or refactoring you make, provide:
1. What was changed.
2. Why the change was made.
3. Which files were modified.
4. How the implementation works.
5. Why this approach was chosen instead of alternatives.
6. Any advantages or disadvantages.
7. Any security considerations.
8. Any limitations.
9. How I can explain this decision to my university supervisor or examiner.

After implementing each feature, generate a report section containing:
- Feature name.
- Objective.
- Design decisions.
- Technologies used.
- Implementation summary.
- Testing performed.
- Expected outcome.
- Potential future improvements.

WHEN WRITING CODE:
- Explain the code before presenting it.
- Add comments throughout the code to aid understanding.
- Keep functions reasonably short and well named.
- Follow consistent formatting and naming conventions.

WHEN CREATING DATABASES:
- Explain each table and relationship.
- Explain why each field exists.
- Explain primary keys and foreign keys.
- Explain how the schema supports the application's functionality.

WHEN BUILDING PAGES:
- Explain the purpose of the page.
- Explain the role of each form, button, and input.
- Explain how data flows between frontend and backend.

WHEN ADDING SECURITY:
- Explain authentication.
- Explain authorization.
- Explain session management.
- Explain password hashing.
- Explain input validation.
- Explain protection against common web vulnerabilities where relevant.

WHEN TESTING:
- Explain how to manually test the feature.
- Suggest edge cases.
- Describe expected results.

WHEN REFACTORING:
- State exactly what changed.
- Explain why the previous implementation was improved.
- Explain any impact on performance, maintainability, or security.

REPORTING:
Maintain a running CHANGELOG in Markdown format that records every modification in chronological order with:
- Date/time (or sequence number),
- Description of the change,
- Reason for the change,
- Files affected,
- Impact on the project.

Also maintain a DESIGN_DECISIONS.md file that records architectural choices and their justifications.

Finally, whenever you produce code, assume I may be asked to explain it in a viva or project presentation. Therefore, provide explanations that help me understand the implementation and the reasoning behind it rather than simply generating code.