package com.recruitment.webapp.service;

import com.recruitment.webapp.dto.JobDescriptionRequest;
import com.recruitment.webapp.dto.ScreenResponse;
import com.recruitment.webapp.dto.ScreenResultItem;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

/** Thin wrapper around the Python FastAPI resume-screening service. */
@Service
public class ScreeningApiClient {

    private static final String API_KEY_HEADER = "X-API-Key";

    private final RestTemplate restTemplate;

    @Value("${api.baseUrl}")
    private String apiBaseUrl;

    @Value("${api.key:}")
    private String apiKey;

    @Autowired
    public ScreeningApiClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    public ScreenResponse screen(JobDescriptionRequest jobDescription) {
        String url = apiBaseUrl + "/screen";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        if (apiKey != null && !apiKey.isEmpty()) {
            headers.set(API_KEY_HEADER, apiKey);
        }

        HttpEntity<JobDescriptionRequest> request = new HttpEntity<>(jobDescription, headers);
        ScreenResponse response = restTemplate.exchange(url, HttpMethod.POST, request, ScreenResponse.class).getBody();

        if (response != null && response.getResults() != null) {
            for (ScreenResultItem item : response.getResults()) {
                item.setResumeLink(resolveResumeLink(item.getResumeLink()));
            }
        }
        return response;
    }

    /** The API returns resume links relative to its own origin (e.g. "/resumes/x.docx"); make them absolute. */
    private String resolveResumeLink(String resumeLink) {
        if (resumeLink == null || resumeLink.isEmpty() || resumeLink.startsWith("http")) {
            return resumeLink;
        }
        return apiBaseUrl + resumeLink;
    }
}
