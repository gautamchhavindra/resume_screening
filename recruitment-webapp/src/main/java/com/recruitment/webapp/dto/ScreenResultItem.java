package com.recruitment.webapp.dto;

/** Mirrors the FastAPI ScreenResultItem schema (flat, JSP-friendly). */
public class ScreenResultItem {

    private String candidateName;
    private String location;
    private String skills;
    private String resumeLink;
    private double similarityScore;
    private int llmScore;
    private String recommendation;

    public String getCandidateName() {
        return candidateName;
    }

    public void setCandidateName(String candidateName) {
        this.candidateName = candidateName;
    }

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

    public String getResumeLink() {
        return resumeLink;
    }

    public void setResumeLink(String resumeLink) {
        this.resumeLink = resumeLink;
    }

    public double getSimilarityScore() {
        return similarityScore;
    }

    public void setSimilarityScore(double similarityScore) {
        this.similarityScore = similarityScore;
    }

    public int getLlmScore() {
        return llmScore;
    }

    public void setLlmScore(int llmScore) {
        this.llmScore = llmScore;
    }

    public String getRecommendation() {
        return recommendation;
    }

    public void setRecommendation(String recommendation) {
        this.recommendation = recommendation;
    }
}
