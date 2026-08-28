package com.recruitment.webapp.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Mirrors the FastAPI JobDescriptionRequest schema. Field names on the wire
 * are snake_case for other_details to match the Python API exactly.
 */
public class JobDescriptionRequest {

    private String location = "";
    private String skills = "";

    @JsonProperty("other_details")
    private String otherDetails = "";

    public String getLocation() {
        return location;
    }

    public void setLocation(String location) {
        this.location = location;
    }

    public String getSkills() {
        return skills;
    }

    public void setSkills(String skills) {
        this.skills = skills;
    }

    public String getOtherDetails() {
        return otherDetails;
    }

    public void setOtherDetails(String otherDetails) {
        this.otherDetails = otherDetails;
    }
}
