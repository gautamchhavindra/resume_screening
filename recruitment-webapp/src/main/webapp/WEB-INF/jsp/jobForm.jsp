<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<!DOCTYPE html>
<html>
<head>
    <title>Resume Screening</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; }
        label { display: block; margin-top: 12px; font-weight: bold; }
        input[type=text], textarea { width: 100%; padding: 6px; box-sizing: border-box; }
        textarea { height: 70px; }
        button { margin-top: 16px; padding: 8px 20px; }
    </style>
</head>
<body>
<h1>Resume Screening</h1>
<p>Enter the job description to rank and screen candidate resumes.</p>

<form action="${pageContext.request.contextPath}/screen" method="post">
    <label for="location">Location</label>
    <input type="text" id="location" name="location" placeholder="e.g. Remote, Austin TX"/>

    <label for="skills">Skills</label>
    <input type="text" id="skills" name="skills" placeholder="e.g. Python, FastAPI, AWS"/>

    <label for="otherDetails">Other Details</label>
    <textarea id="otherDetails" name="otherDetails" placeholder="Experience level, domain, certifications, etc."></textarea>

    <button type="submit">Screen Candidates</button>
</form>
</body>
</html>
