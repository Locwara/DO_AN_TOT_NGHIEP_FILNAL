"""File storage service.

Wraps Cloudinary operations (upload, download URL, delete) behind a
simple interface.  The rest of the codebase calls these helpers instead
of using Cloudinary directly so the storage backend can be swapped later.
"""
import logging
import cloudinary
import cloudinary.uploader
import cloudinary.api

logger = logging.getLogger(__name__)


def upload_file(file_obj, folder='assignments', resource_type='auto', public_id=None):
    """Upload a file to Cloudinary.

    Args:
        file_obj:       A Django UploadedFile, file-like object, or file path string.
        folder:         Cloudinary folder path (e.g. 'assignments', 'avatars').
        resource_type:  'auto', 'image', 'raw', or 'video'.
        public_id:      Optional explicit public ID.

    Returns:
        dict with keys:
            url         – secure HTTPS URL
            public_id   – Cloudinary public ID
            file_size   – size in bytes
            format      – file extension / format
            resource_type
    """
    upload_kwargs = {
        'folder': folder,
        'resource_type': resource_type,
        'overwrite': True,
    }
    if public_id:
        upload_kwargs['public_id'] = public_id

    result = cloudinary.uploader.upload(file_obj, **upload_kwargs)

    return {
        'url': result.get('secure_url', result.get('url', '')),
        'public_id': result.get('public_id', ''),
        'file_size': result.get('bytes', 0),
        'format': result.get('format', ''),
        'resource_type': result.get('resource_type', resource_type),
    }


def delete_file(public_id, resource_type='image'):
    """Delete a file from Cloudinary by its public_id.

    Returns:
        True if successfully deleted, False otherwise.
    """
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        return result.get('result') == 'ok'
    except Exception:
        logger.exception('Failed to delete file %s', public_id)
        return False


def get_file_url(public_id, resource_type='image', transformation=None):
    """Generate a Cloudinary URL for the given public_id.

    Args:
        public_id:      Cloudinary public ID.
        resource_type:  'image', 'raw', 'video'.
        transformation: Optional dict of Cloudinary transformations.

    Returns:
        Secure HTTPS URL string.
    """
    options = {'secure': True, 'resource_type': resource_type}
    if transformation:
        options['transformation'] = transformation
    url, _opts = cloudinary.utils.cloudinary_url(public_id, **options)
    return url


def upload_avatar(file_obj, user_id):
    """Upload a user avatar with standard transformations."""
    return upload_file(
        file_obj,
        folder='avatars',
        resource_type='image',
        public_id=f'avatar_{user_id}',
    )


def upload_assignment_file(file_obj, assignment_id, file_name):
    """Upload an assignment attachment."""
    safe_name = file_name.rsplit('.', 1)[0] if '.' in file_name else file_name
    return upload_file(
        file_obj,
        folder=f'assignments/{assignment_id}',
        resource_type='raw',
        public_id=safe_name,
    )


def list_files(folder, resource_type='raw', max_results=100):
    """List files in a Cloudinary folder.

    Returns:
        list of dicts with keys: public_id, url, file_size, created_at
    """
    try:
        result = cloudinary.api.resources(
            type='upload',
            prefix=folder,
            resource_type=resource_type,
            max_results=max_results,
        )
        files = []
        for r in result.get('resources', []):
            files.append({
                'public_id': r.get('public_id', ''),
                'url': r.get('secure_url', r.get('url', '')),
                'file_size': r.get('bytes', 0),
                'created_at': r.get('created_at', ''),
            })
        return files
    except Exception:
        logger.exception('Failed to list files in folder %s', folder)
        return []
