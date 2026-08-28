package com.recruitment.webapp.controller;

import com.recruitment.webapp.dto.JobDescriptionRequest;
import com.recruitment.webapp.dto.ScreenResponse;
import com.recruitment.webapp.service.ScreeningApiClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.client.RestClientException;

@Controller
@RequestMapping("/screen")
public class ScreeningController {

    private final ScreeningApiClient apiClient;

    @Autowired
    public ScreeningController(ScreeningApiClient apiClient) {
        this.apiClient = apiClient;
    }

    @GetMapping
    public String showForm(Model model) {
        model.addAttribute("jobDescription", new JobDescriptionRequest());
        return "jobForm";
    }

    @PostMapping
    public String submit(@ModelAttribute("jobDescription") JobDescriptionRequest jobDescription, Model model) {
        long startTime = System.currentTimeMillis();
        try {
            ScreenResponse response = apiClient.screen(jobDescription);
            model.addAttribute("jobId", response != null ? response.getJobId() : null);
            model.addAttribute("results", response != null ? response.getResults() : null);
        } catch (RestClientException ex) {
            model.addAttribute("errorMessage", "Could not reach the screening API: " + ex.getMessage());
        }
        System.out.println("Test");     
        double elapsedSeconds = (System.currentTimeMillis() - startTime) / 1000.0;
        model.addAttribute("elapsedSeconds", String.format("%.1f", elapsedSeconds));
        return "results";
    }
}
