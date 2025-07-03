"""Agent Scheduler - Framework-agnostic agent scheduling and lifecycle management.

This module provides interfaces and implementations for:
- Agent resource scheduling
- Lifecycle management
- Load balancing (future)
- Resource allocation and cleanup
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from ..models import AgentCreateRequest
from .agent_factory import AgentFactoryInterface

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent lifecycle status."""
    CREATING = "creating"
    ACTIVE = "active"
    BUSY = "busy"
    IDLE = "idle"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class SchedulerInterface(ABC):
    """Interface for agent scheduler implementations."""
    
    @abstractmethod
    async def schedule_agent_creation(self, agent_data: AgentCreateRequest) -> str:
        """Schedule agent creation and return task ID."""
        pass
    
    @abstractmethod
    async def schedule_agent_deletion(self, agent_id: str) -> bool:
        """Schedule agent deletion."""
        pass
    
    @abstractmethod
    def get_agent_status(self, agent_id: str) -> Optional[AgentStatus]:
        """Get current status of an agent."""
        pass
    
    @abstractmethod
    def list_scheduled_tasks(self) -> list[dict[str, Any]]:
        """List all scheduled tasks."""
        pass
    
    @abstractmethod
    async def cleanup_idle_agents(self, idle_timeout: timedelta) -> int:
        """Clean up agents that have been idle for too long."""
        pass


class AgentScheduler(SchedulerInterface):
    """
    Main agent scheduler with resource management.
    
    Features:
    - Asynchronous agent lifecycle management
    - Resource allocation and tracking
    - Idle agent cleanup
    - Task scheduling and monitoring
    """
    
    def __init__(self, agent_factory: AgentFactoryInterface, max_concurrent_agents: int = 100):
        self.agent_factory = agent_factory
        self.max_concurrent_agents = max_concurrent_agents
        
        # Agent status tracking
        self.agent_status: dict[str, AgentStatus] = {}
        self.agent_last_activity: dict[str, datetime] = {}
        
        # Task tracking
        self.scheduled_tasks: dict[str, dict[str, Any]] = {}
        self.task_counter = 0
        
        # Resource tracking
        self.resource_usage: dict[str, Any] = {
            "memory_mb": 0,
            "cpu_cores": 0.0,
            "active_agents": 0,
        }
        
        # Cleanup settings
        self.default_idle_timeout = timedelta(hours=1)
        self.cleanup_interval = timedelta(minutes=30)
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.monitoring_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the scheduler and background tasks."""
        # Start background cleanup task
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._periodic_monitoring())
        
        logger.info("Agent scheduler started")
    
    async def stop(self) -> None:
        """Stop the scheduler and background tasks."""
        # Cancel background tasks
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Clean up all agents
        await self._cleanup_all_agents()
        
        logger.info("Agent scheduler stopped")
    
    async def schedule_agent_creation(self, agent_data: AgentCreateRequest) -> str:
        """
        Schedule agent creation and return task ID.
        
        Args:
            agent_data: Agent creation request
            
        Returns:
            Task ID for tracking
            
        Raises:
            RuntimeError: If resource limits exceeded
        """
        # Check resource limits
        if len(self.agent_status) >= self.max_concurrent_agents:
            raise RuntimeError(f"Maximum concurrent agents ({self.max_concurrent_agents}) reached")
        
        # Generate task ID
        task_id = f"create-{self.task_counter}"
        self.task_counter += 1
        
        # Track the task
        self.scheduled_tasks[task_id] = {
            "type": "create_agent",
            "agent_id": agent_data.id,
            "status": "scheduled",
            "created_at": datetime.now(),
            "agent_data": agent_data,
        }
        
        # Set initial status
        self.agent_status[agent_data.id] = AgentStatus.CREATING
        
        # Schedule the creation task
        asyncio.create_task(self._execute_agent_creation(task_id, agent_data))
        
        logger.info(f"Scheduled agent creation: {agent_data.id} (task: {task_id})")
        return task_id
    
    async def schedule_agent_deletion(self, agent_id: str) -> bool:
        """
        Schedule agent deletion.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if deletion scheduled, False if agent not found
        """
        if agent_id not in self.agent_status:
            return False
        
        # Generate task ID
        task_id = f"delete-{self.task_counter}"
        self.task_counter += 1
        
        # Track the task
        self.scheduled_tasks[task_id] = {
            "type": "delete_agent",
            "agent_id": agent_id,
            "status": "scheduled",
            "created_at": datetime.now(),
        }
        
        # Update status
        self.agent_status[agent_id] = AgentStatus.STOPPING
        
        # Schedule the deletion task
        asyncio.create_task(self._execute_agent_deletion(task_id, agent_id))
        
        logger.info(f"Scheduled agent deletion: {agent_id} (task: {task_id})")
        return True
    
    def get_agent_status(self, agent_id: str) -> Optional[AgentStatus]:
        """Get current status of an agent."""
        return self.agent_status.get(agent_id)
    
    def set_agent_busy(self, agent_id: str) -> None:
        """Mark an agent as busy."""
        if agent_id in self.agent_status:
            self.agent_status[agent_id] = AgentStatus.BUSY
            self.agent_last_activity[agent_id] = datetime.now()
    
    def set_agent_idle(self, agent_id: str) -> None:
        """Mark an agent as idle."""
        if agent_id in self.agent_status:
            self.agent_status[agent_id] = AgentStatus.IDLE
            self.agent_last_activity[agent_id] = datetime.now()
    
    def update_agent_activity(self, agent_id: str) -> None:
        """Update last activity timestamp for an agent."""
        self.agent_last_activity[agent_id] = datetime.now()
    
    def list_scheduled_tasks(self) -> list[dict[str, Any]]:
        """List all scheduled tasks."""
        return list(self.scheduled_tasks.values())
    
    async def cleanup_idle_agents(self, idle_timeout: Optional[timedelta] = None) -> int:
        """
        Clean up agents that have been idle for too long.
        
        Args:
            idle_timeout: Maximum idle time before cleanup
            
        Returns:
            Number of agents cleaned up
        """
        if idle_timeout is None:
            idle_timeout = self.default_idle_timeout
        
        cutoff_time = datetime.now() - idle_timeout
        agents_to_cleanup = []
        
        for agent_id, status in self.agent_status.items():
            if status == AgentStatus.IDLE:
                last_activity = self.agent_last_activity.get(agent_id, datetime.now())
                if last_activity < cutoff_time:
                    agents_to_cleanup.append(agent_id)
        
        # Clean up idle agents
        cleanup_count = 0
        for agent_id in agents_to_cleanup:
            success = await self.schedule_agent_deletion(agent_id)
            if success:
                cleanup_count += 1
        
        if cleanup_count > 0:
            logger.info(f"Cleaned up {cleanup_count} idle agents")
        
        return cleanup_count
    
    def get_resource_usage(self) -> dict[str, Any]:
        """Get current resource usage statistics."""
        active_count = sum(1 for status in self.agent_status.values() 
                          if status in [AgentStatus.ACTIVE, AgentStatus.BUSY])
        
        self.resource_usage["active_agents"] = active_count
        return self.resource_usage.copy()
    
    def get_stats(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        status_counts = {}
        for status in AgentStatus:
            status_counts[status.value] = sum(1 for s in self.agent_status.values() if s == status)
        
        return {
            "total_agents": len(self.agent_status),
            "max_concurrent_agents": self.max_concurrent_agents,
            "status_distribution": status_counts,
            "pending_tasks": len([t for t in self.scheduled_tasks.values() if t["status"] == "scheduled"]),
            "resource_usage": self.get_resource_usage(),
        }
    
    async def _execute_agent_creation(self, task_id: str, agent_data: AgentCreateRequest) -> None:
        """Execute agent creation task."""
        try:
            # Update task status
            self.scheduled_tasks[task_id]["status"] = "running"
            
            # Create the agent
            agent = self.agent_factory.create_agent(agent_data)
            
            # Update status
            self.agent_status[agent_data.id] = AgentStatus.ACTIVE
            self.agent_last_activity[agent_data.id] = datetime.now()
            
            # Update task
            self.scheduled_tasks[task_id]["status"] = "completed"
            self.scheduled_tasks[task_id]["completed_at"] = datetime.now()
            
            logger.info(f"Agent creation completed: {agent_data.id}")
            
        except Exception as e:
            # Handle creation failure
            self.agent_status[agent_data.id] = AgentStatus.ERROR
            self.scheduled_tasks[task_id]["status"] = "failed"
            self.scheduled_tasks[task_id]["error"] = str(e)
            self.scheduled_tasks[task_id]["completed_at"] = datetime.now()
            
            logger.error(f"Agent creation failed: {agent_data.id} - {e}")
    
    async def _execute_agent_deletion(self, task_id: str, agent_id: str) -> None:
        """Execute agent deletion task."""
        try:
            # Update task status
            self.scheduled_tasks[task_id]["status"] = "running"
            
            # Delete the agent
            success = self.agent_factory.destroy_agent(agent_id)
            
            if success:
                # Clean up tracking
                del self.agent_status[agent_id]
                if agent_id in self.agent_last_activity:
                    del self.agent_last_activity[agent_id]
                
                # Update task
                self.scheduled_tasks[task_id]["status"] = "completed"
                self.scheduled_tasks[task_id]["completed_at"] = datetime.now()
                
                logger.info(f"Agent deletion completed: {agent_id}")
            else:
                raise RuntimeError(f"Failed to delete agent {agent_id}")
                
        except Exception as e:
            # Handle deletion failure
            self.agent_status[agent_id] = AgentStatus.ERROR
            self.scheduled_tasks[task_id]["status"] = "failed"
            self.scheduled_tasks[task_id]["error"] = str(e)
            self.scheduled_tasks[task_id]["completed_at"] = datetime.now()
            
            logger.error(f"Agent deletion failed: {agent_id} - {e}")
    
    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of idle agents."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval.total_seconds())
                await self.cleanup_idle_agents()
                
                # Clean up old completed tasks
                await self._cleanup_old_tasks()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic cleanup error: {e}")
    
    async def _periodic_monitoring(self) -> None:
        """Periodic monitoring and logging."""
        while True:
            try:
                await asyncio.sleep(300)  # 5 minutes
                
                stats = self.get_stats()
                logger.info(f"Scheduler stats: {stats}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic monitoring error: {e}")
    
    async def _cleanup_old_tasks(self) -> None:
        """Clean up old completed tasks."""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        tasks_to_remove = []
        for task_id, task_info in self.scheduled_tasks.items():
            if (task_info["status"] in ["completed", "failed"] and 
                task_info.get("completed_at", datetime.now()) < cutoff_time):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.scheduled_tasks[task_id]
        
        if tasks_to_remove:
            logger.debug(f"Cleaned up {len(tasks_to_remove)} old tasks")
    
    async def _cleanup_all_agents(self) -> None:
        """Clean up all agents on shutdown."""
        agent_ids = list(self.agent_status.keys())
        for agent_id in agent_ids:
            try:
                self.agent_factory.destroy_agent(agent_id)
            except Exception as e:
                logger.error(f"Failed to cleanup agent {agent_id}: {e}")
        
        self.agent_status.clear()
        self.agent_last_activity.clear() 