# Recruitment Screening WebApp (Spring MVC 5 + JSP)

A minimal legacy-style Spring MVC 5.0 / JSP client for the Python resume-screening
REST API (`../api.py`). Submits a job description form, calls `POST /screen`, and
renders the results in a table: candidate name, location, skills, and a link to
the resume.

## Stack

- Spring MVC 5.0.9.RELEASE (XML config: `web.xml` + `spring-servlet.xml`, no Spring Boot)
- JSP + JSTL views, `InternalResourceViewResolver`
- `RestTemplate` (Jackson on the classpath) to call the FastAPI service
- Packaged as a WAR, deployable to any Servlet 4.0 container (Tomcat 8.5+/9)

## Project layout

```
src/main/java/com/recruitment/webapp/
  config/AppConfig.java        RestTemplate bean
  controller/ScreeningController.java   GET/POST /screen
  service/ScreeningApiClient.java       calls the Python API, resolves resume links
  dto/                          JobDescriptionRequest, ScreenResponse, ScreenResultItem
src/main/resources/application.properties   api.baseUrl
src/main/webapp/
  WEB-INF/web.xml, spring-servlet.xml
  WEB-INF/jsp/jobForm.jsp, results.jsp
  index.jsp                    redirects to /screen
```

## Setup

Requires Java 8+ and Maven. Point it at your running Python API by editing
`src/main/resources/application.properties`:

```properties
api.baseUrl=http://localhost:8000
api.key=${RECRUITMENT_API_KEY:}
```

If the Python API has `RECRUITMENT_API_KEY` set (see its README), set the same value in the
`RECRUITMENT_API_KEY` environment variable before starting this app — `ScreeningApiClient` sends it
as an `X-API-Key` header on every call. Leave it unset on both sides for no-auth (the default).

## Running

1. Start the Python API first (from `../resume-screening-agent`):

   ```bash
   cd ../resume-screening-agent
   uvicorn api:app --reload --port 8000
   ```

2. Run the webapp with the embedded Tomcat Maven plugin (fastest for local dev,
   no separate Tomcat install needed):

   ```bash
   mvn tomcat7:run
   ```

   Then open http://localhost:8082/

   Or build a WAR and deploy it to an external Tomcat:

   ```bash
   mvn clean package
   # copy target/recruitment-webapp.war to <TOMCAT_HOME>/webapps/
   ```

## Flow

1. `GET /screen` — shows the job description form (location, skills, other details).
2. `POST /screen` — `ScreeningController` binds the form to `JobDescriptionRequest`,
   `ScreeningApiClient` POSTs it as JSON to the Python API's `/screen`, and the
   resulting `results` list is placed on the model.
3. `results.jsp` iterates the list with JSTL `<c:forEach>` — no manual JSON parsing,
   since Spring's `RestTemplate` + Jackson already deserialized it into typed
   `ScreenResultItem` objects.
4. Resume links come back from the API as paths relative to its own origin (e.g.
   `/resumes/jane_doe.docx`); `ScreeningApiClient` resolves them to absolute URLs
   using `api.baseUrl` before they reach the JSP.

## Notes

- No auth, matching the underlying API (see [`../resume-screening-agent/README.md`](../resume-screening-agent/README.md) assumptions).
- If the Python API is unreachable, `results.jsp` shows an error message instead
  of a stack trace.
