# ☁️ Azure Deployment Plan

This document outlines the strategy for deploying the MOODZ platform to Microsoft Azure.

## 🏛️ Architecture Overview

The MOODZ application consists of the following components:
- **Frontend**: Angular SPA
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Cache**: Redis
- **AI Services**: OpenAI, Google Gemini, Pinecone (External)

For deployment, we will utilize Azure's modern cloud-native services to ensure scalability, reliability, and security.

## 📦 Selected Azure Services

1. **Compute (Microservices Host)**
   - **Azure Container Apps (ACA)**: We will deploy both the Angular frontend (served via Nginx) and the FastAPI backend as separate container apps. ACA is ideal for microservices, providing automatic scaling (including scale-to-zero) and built-in HTTP ingress.
   - Alternatively, Azure App Service for Containers can be used for simpler, single-container deployments.

2. **Database Layer**
   - **Azure Database for PostgreSQL - Flexible Server**: A managed PostgreSQL service that offers high availability, automated backups, and flexible scaling.

3. **Caching Layer**
   - **Azure Cache for Redis**: A fully managed in-memory cache to handle fast session retrieval and chat history buffering.

4. **Container Registry**
   - **Azure Container Registry (ACR)**: A private registry to build, store, and manage the Docker images for the frontend and backend.

5. **Secrets Management**
   - **Azure Key Vault**: To securely store sensitive environment variables such as the `OPENAI_API_KEY`, `GEMINI_API_KEY`, `PINECONE_API_KEY`, and database passwords.

## 🚀 Deployment Steps

### 1. Provision Infrastructure
- Create an Azure Resource Group.
- Provision the Azure Container Registry (ACR).
- Provision the Azure Database for PostgreSQL and Azure Cache for Redis. Ensure virtual network (VNet) rules allow access from your Azure Container Apps.
- Create an Azure Key Vault and store all secrets.

### 2. Build and Push Container Images
Build the Docker images using the existing `Dockerfile` and push them to the Azure Container Registry.

```bash
# Example commands
az acr login --name <your_acr_name>

# Build and push Backend
docker build -t <your_acr_name>.azurecr.io/moodz-backend:latest "./MOOD AI AGENT"
docker push <your_acr_name>.azurecr.io/moodz-backend:latest

# Build and push Frontend
docker build -t <your_acr_name>.azurecr.io/moodz-frontend:latest ./moodz-frontend
docker push <your_acr_name>.azurecr.io/moodz-frontend:latest
```

### 3. Deploy to Azure Container Apps
- Create an Azure Container Apps Environment.
- Deploy the **Backend** container app. Configure environment variables, referencing the Key Vault for secrets.
- Deploy the **Frontend** container app. Configure it to communicate with the Backend's FQDN (Fully Qualified Domain Name). Enable external HTTP ingress.

### 4. Configure CI/CD (Optional but Recommended)
Set up GitHub Actions to automate the build and deployment process:
- Trigger on pushes to the `main` branch.
- Log into Azure CLI.
- Build and push the Docker images to ACR.
- Update the Azure Container Apps with the newly built image tags.

## 🔒 Security & Networking
- Restrict access to the PostgreSQL database and Redis cache to only the IP addresses/subnets used by the Azure Container Apps.
- Use Managed Identities for the Container Apps to access the Azure Key Vault without needing connection strings.

## 💰 Cost Optimization
- Utilize the Azure Container Apps "Consumption" workload profile to only pay for the compute resources used when the app is active.
- Start with lower-tier SKUs for PostgreSQL and Redis during initial testing.
