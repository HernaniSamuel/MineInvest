import { toast } from 'react-toastify';

export const showToast = {
    success: (message) => {
        toast.success(message, {
            icon: "✅",
        });
    },
    
    error: (message) => {
        toast.error(message, {
            icon: "❌",
        });
    },
    
    info: (message) => {
        toast.info(message, {
            icon: "ℹ️",
        });
    },
    
    warning: (message) => {
        toast.warning(message, {
            icon: "⚠️",
        });
    },
    
    loading: (message) => {
        return toast.loading(message);
    },
    
    update: (toastId, type, message) => {
        toast.update(toastId, {
            render: message,
            type: type,
            isLoading: false,
            autoClose: 3000,
        });
    }
};