# Stage 1: Build the WAR file using Maven
FROM maven:3.8.6-openjdk-8-slim AS build
WORKDIR /app
COPY pom.xml .
# Download dependencies first to cache this layer
RUN mvn dependency:go-offline -B

# Copy the source code and build the WAR
COPY src ./src
RUN mvn clean package -DskipTests

# Stage 2: Run the application in Tomcat
FROM tomcat:9.0-jre8-alpine

# Remove default Tomcat apps to keep it clean and ensure our app runs at the root (/)
RUN rm -rf /usr/local/tomcat/webapps/*

# Copy the built WAR file from the build stage into the Tomcat webapps directory as ROOT.war
COPY --from=build /app/target/recruitment-webapp.war /usr/local/tomcat/webapps/ROOT.war

# Tomcat listens on 8080 by default
EXPOSE 8080

CMD ["catalina.sh", "run"]
