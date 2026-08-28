<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
<!DOCTYPE html>
<html>
<head>
    <title>Screening Results</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; }
        table { border-collapse: collapse; width: 100%; margin-top: 16px; }
        th, td { border: 1px solid #ccc; padding: 8px 10px; text-align: left; vertical-align: top; }
        th { background: #f2f2f2; }
        .error { color: #b00020; font-weight: bold; }
        .empty { color: #666; }
        .score-warning { color: #b00020; }
        .timing { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
<h1>Candidate Screening Results</h1>

<c:if test="${not empty elapsedSeconds}">
    <p class="timing">Completed in ${elapsedSeconds} seconds</p>
</c:if>

<c:if test="${not empty errorMessage}">
    <p class="error">${errorMessage}</p>
</c:if>

<c:if test="${empty errorMessage}">
    <c:choose>
        <c:when test="${empty results}">
            <p class="empty">No candidates matched this job description.</p>
        </c:when>
        <c:otherwise>
            <table>
                <tr>
                    <th>Candidate Name</th>
                    <th>Location</th>
                    <th>Skills</th>
                    <th>Similarity</th>
                    <th>Match Score</th>
                    <th>Recommendation</th>
                    <th>Resume</th>
                </tr>
                <c:forEach var="result" items="${results}">
                    <tr>
                        <td>${result.candidateName}</td>
                        <td>${result.location}</td>
                        <td>${result.skills}</td>
                        <td>${result.similarityScore}</td>
                        <td>
                            <c:choose>
                                <c:when test="${result.llmScore == 0}">
                                    <span class="score-warning">0 (scoring failed — check DEEPSEEK_API_KEY)</span>
                                </c:when>
                                <c:otherwise>${result.llmScore}</c:otherwise>
                            </c:choose>
                        </td>
                        <td>${result.recommendation}</td>
                        <td><a href="${result.resumeLink}" target="_blank" rel="noopener">View Resume</a></td>
                    </tr>
                </c:forEach>
            </table>
        </c:otherwise>
    </c:choose>
</c:if>

<p><a href="${pageContext.request.contextPath}/screen">New search</a></p>
</body>
</html>
