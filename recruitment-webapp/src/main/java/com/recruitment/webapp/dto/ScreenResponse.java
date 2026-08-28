package com.recruitment.webapp.dto;

import java.util.List;

/** Mirrors the FastAPI ScreenResponse schema. */
public class ScreenResponse {

    private String jobId;
    private List<ScreenResultItem> results;

    public String getJobId() {
        return jobId;
    }

    public void setJobId(String jobId) {
        this.jobId = jobId;
    }

    public List<ScreenResultItem> getResults() {
        return results;
    }

    public void setResults(List<ScreenResultItem> results) {
        this.results = results;
    }
}
