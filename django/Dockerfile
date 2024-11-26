FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    iproute2 \
    libpq-dev \
    libssl-dev \
    psmisc \
    sudo \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Add a flash user and give sudo permissions without password
RUN adduser --disabled-password --gecos "" flash && \
    echo 'flash ALL=(ALL) NOPASSWD: ALL' >> /etc/sudoers

# Set the working directory
WORKDIR /home/flash

# Copy the requirements file and install Python dependencies
COPY flashdb/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /home/flash/django

# IP address used to check route to external-facing interface
ENV IPCHECK=150.229.69.37

# Copy service files and certificates
COPY docker/service/* /home/flash/django/flashdb/service/
COPY docker/certs/*    /home/flash/django/flashdb/certs/

# Set ownership and permissions
RUN chown -R flash:flash /home/flash && \
    rm -rf /home/flash/django/docker

COPY docker/service/flashdb.sh /usr/local/bin
RUN chmod a+x /usr/local/bin/flashdb.sh

# Display contents of the directory for debugging
RUN echo "Contents of /home/flash/django/flashdb/flashdb/" && \
    ls -la /home/flash/django/flashdb/flashdb/

# Switch to the flash user
USER flash

# Expose port 443
EXPOSE 443

# Start the application
CMD [ "/usr/local/bin/flashdb.sh" ]