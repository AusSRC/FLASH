This folder contains ansible scripts for making a Flash dev or production 
VM from scratch. 

To make a dev VM, first make it using Oracle Cloud Compute UI and select 
Ubuntu 24 as your image, then once its up:

1) Make secrets/files/dev/secrets.env with appropriate entries
2) Put your Cloudflare Origin Certificate for the dev domain in ssl/files/dev/fullchain.pem 
3) Put your Cloudflare Origin Private Key for the dev domain in ssl/files/dev/privkey.pem
4) Update ansible/inventories/dev/hosts.ini's 'ansible_host' to be your premade ubuntu 24 VM host and the 'ansible_ssh_private_key_file' to be the local location of the key you added/made during VM creation
5) IMPORTANT!!! Add the public_key made during the VM creation to ansible/inventories/dev/group_vars/all.yml under 'ssh_public_keys' along with any other keys you want on there, generally it should look like:

```
ssh_public_keys:
 - "ssh-ed25519 the_admin_publickey_here admin_key"
 - "ssh-ed25519 some_devs_publickey_here somedev@somedevlaptop"
 - "ssh-ed25519 some_other_devs_publickey_here someotherdev@someotherdevlaptop"
```

6) IMPORTANT!!! If you don't do step 5 right you will lock yourself out the VM
7) Generate a ssh-key for github, put the private key file in github secrets and the public in inventories/dev/group_vars/all.yml github_deploy_ssh_key property
4) cd FLASH/ansible/
5) ansible-playbook site.yml -i inventories/dev/hosts.ini

Production VMs are identical but will need prod instead of dev in all steps 
and will need the production Cloudflare Origin Cert & Key